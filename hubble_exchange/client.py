import json
from typing import List

import websockets
from hexbytes import HexBytes

from hubble_exchange.eth import get_async_web3_client, get_websocket_endpoint
from hubble_exchange.models import (AsyncOrderBookDepthCallback,
                                    AsyncOrderStatusCallback,
                                    AsyncPlaceOrdersCallback,
                                    AsyncPositionCallback,
                                    AsyncSubscribeToOrderBookDepthCallback,
                                    Order, OrderBookDepthUpdateResponse,
                                    OrderStatusResponse, WebsocketResponse)
from hubble_exchange.order_book import OrderBookClient, TransactionMode
from hubble_exchange.utils import (float_to_scaled_int,
                                   get_address_from_private_key, get_new_salt)


class HubbleClient:
    def __init__(self, private_key: str):
        if not private_key:
            raise ValueError("Private key is not set")
        self.trader_address = get_address_from_private_key(private_key)
        if not self.trader_address:
            raise ValueError("Cannot determine trader address from private key")

        self.web3_client = get_async_web3_client()
        self.websocket_endpoint = get_websocket_endpoint()
        self.order_book_client = OrderBookClient(private_key)

    def set_transaction_mode(self, mode: TransactionMode):
        self.order_book_client.set_transaction_mode(mode)

    async def get_order_book(self, market: int, callback: AsyncOrderBookDepthCallback):
        order_book_depth = await self.web3_client.eth.get_order_book_depth(market)
        return await callback(order_book_depth)

    async def get_margin_and_positions(self, callback: AsyncPositionCallback):
        response = await self.web3_client.eth.get_margin_and_positions(self.trader_address)
        return await callback(response)

    async def get_order_status(self, order_id: HexBytes, callback: AsyncOrderStatusCallback):
        response = await self.web3_client.eth.get_order_status(order_id.hex()) # type: ignore
        return await callback(response)

    async def place_orders(self, orders: List[Order], callback: AsyncPlaceOrdersCallback, tx_options = None, mode=None):
        if len(orders) > 75:
            raise ValueError("Cannot place more than 75 orders at once")

        for order in orders:
            if order.amm_index is None:
                raise ValueError("Order AMM index is not set")
            if order.base_asset_quantity is None:
                raise ValueError("Order base asset quantity is not set")
            if order.price is None:
                raise ValueError("Order price is not set")
            if order.reduce_only is None:
                raise ValueError("Order reduce only is not set")

            # trader and salt can be set automatically
            if order.trader in [None, "0x", ""]:
                order.trader = self.trader_address
            if order.salt in [None, 0]:
                order.salt = get_new_salt()

        response = await self.order_book_client.place_orders(orders, tx_options, mode)
        return await callback(response)

    async def place_single_order(
        self, market: int, base_asset_quantity: float, price: float, reduce_only: bool, callback, tx_options = None, mode=None
    ) -> Order:
        order = Order(
            id=None,
            amm_index=market,
            trader=self.trader_address,
            base_asset_quantity=float_to_scaled_int(base_asset_quantity, 18),
            price=float_to_scaled_int(price, 6),
            salt=get_new_salt(),
            reduce_only=reduce_only,
        )
        order_hash = await self.order_book_client.place_order(order, tx_options, mode)
        order.id = order_hash
        return await callback(order)

    async def cancel_orders(self, orders: List[Order], callback, tx_options = None, mode=None):
        if len(orders) > 100:
            raise ValueError("Cannot cancel more than 100 orders at once")

        await self.order_book_client.cancel_orders(orders, tx_options, mode)
        return await callback()

    async def cancel_order_by_id(self, order_id: HexBytes, callback, tx_options = None, mode=None):
        async def order_status_callback(response: OrderStatusResponse) -> Order:
            position_side_multiplier = 1 if response.positionSide == "LONG" else -1
            return Order(
                id=order_id,
                amm_index=response.symbol,
                trader=self.trader_address,
                base_asset_quantity=float_to_scaled_int(float(response.origQty) * position_side_multiplier, 18),
                price=float_to_scaled_int(float(response.price), 6),
                salt=int(response.salt),
                reduce_only=response.reduceOnly,
            )
        order = await self.get_order_status(order_id, order_status_callback)
        response = await self.cancel_orders([order], callback, tx_options, mode)
        return await callback(response)

    async def subscribe_to_order_book_depth(
        self, market: int, callback: AsyncSubscribeToOrderBookDepthCallback
    ) -> None:
        async with websockets.connect(self.websocket_endpoint) as ws:
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "trading_subscribe",
                "params": ["streamDepthUpdateForMarket", market]
            }
            await ws.send(json.dumps(msg))

            async for message in ws:
                message_json = json.loads(message)
                if message_json.get('result'):
                    # ignore because it's a subscription confirmation with subscription id
                    continue
                response = WebsocketResponse(**message_json)
                if response.method and response.method == "trading_subscription":
                    response = OrderBookDepthUpdateResponse(
                        T=response.params['result']['T'],
                        symbol=response.params['result']['s'],
                        bids=response.params['result']['b'],
                        asks=response.params['result']['a'],
                    )
                    await callback(ws, response)
