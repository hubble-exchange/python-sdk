import json
from typing import Any, Callable, List

import websocket
from hexbytes import HexBytes

from hubble_exchange.eth import (get_web3_client,
                                 get_websocket_endpoint)
from hubble_exchange.models import (GetPositionsResponse, Order,
                                    OrderBookDepthResponse,
                                    OrderBookDepthUpdateResponse,
                                    OrderStatusResponse, WebsocketResponse)
from hubble_exchange.order_book import OrderBookClient
from hubble_exchange.utils import (float_to_scaled_int,
                                   get_address_from_private_key, get_new_salt)


class HubbleClient:
    def __init__(self, private_key: str):
        if not private_key:
            raise ValueError("Private key is not set")
        self.trader_address = get_address_from_private_key(private_key)
        if not self.trader_address:
            raise ValueError("Cannot determine trader address from private key")

        self.web3_client = get_web3_client()
        self.websocket_endpoint = get_websocket_endpoint()
        self.order_book_client = OrderBookClient(private_key)

    def get_order_book(self, market: int) -> OrderBookDepthResponse:
        return self.web3_client.eth.get_order_book_depth(market)

    def get_margin_and_positions(self) -> GetPositionsResponse:
        return self.web3_client.eth.get_margin_and_positions(self.trader_address)

    def get_order_status(self, order_id: HexBytes) -> OrderStatusResponse:
        return self.web3_client.eth.get_order_status(order_id.hex())

    def place_orders(self, orders: List[Order], tx_options = None, mode=None) -> List[Order]:
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

        return self.order_book_client.place_orders(orders, tx_options, mode)

    def place_single_order(
        self, market: int, base_asset_quantity: float, price: float, reduce_only: bool, tx_options = None, mode=None
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
        order_hash = self.order_book_client.place_order(order, tx_options, mode)
        order.id = order_hash
        return order

    def cancel_orders(self, orders: List[Order], tx_options = None, mode=None) -> None:
        if len(orders) > 100:
            raise ValueError("Cannot cancel more than 100 orders at once")

        self.order_book_client.cancel_orders(orders, tx_options, mode)

    def cancel_order_by_id(self, order_id: HexBytes, tx_options = None, mode=None) -> None:
        order_status = self.get_order_status(order_id)
        position_side_multiplier = 1 if order_status.positionSide == "LONG" else -1
        order = Order(
            id=order_id.hex(),
            amm_index=order_status.symbol,
            trader=self.trader_address,
            base_asset_quantity=float_to_scaled_int(float(order_status.origQty) * position_side_multiplier, 18),
            price=float_to_scaled_int(float(order_status.price), 6),
            salt=int(order_status.salt),
            reduce_only=order_status.reduceOnly,
        )
        self.cancel_orders([order], tx_options, mode)

    def subscribe_to_order_book_depth(
        self, market: int, callback: Callable[[websocket.WebSocketApp, OrderBookDepthUpdateResponse], Any]
    ) -> None:

        def on_open(ws):
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "trading_subscribe",
                "params": ["streamDepthUpdateForMarket", market]
            }
            ws.send(json.dumps(msg))

        def on_message(ws, message):
            message_json = json.loads(message)
            response = WebsocketResponse(**message_json)
            if response.method and response.method == "trading_subscription":
                response = OrderBookDepthUpdateResponse(
                    T=response.params['result']['T'],
                    symbol=response.params['result']['s'],
                    bids=response.params['result']['b'],
                    asks=response.params['result']['a'],
                )
                callback(ws, response)

        ws = websocket.WebSocketApp(self.websocket_endpoint, on_open=on_open, on_message=on_message)
        ws.run_forever()
