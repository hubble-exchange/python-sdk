import asyncio
import json
import math
import time
from typing import Dict, List

import websockets
from hexbytes import HexBytes
from web3 import Web3

from hubble_exchange.eip712 import (encode_signed_order, get_signature,
                                    get_signed_order_hash)
from hubble_exchange.errors import OrderNotFound
from hubble_exchange.eth import get_async_web3_client, get_websocket_endpoint
from hubble_exchange.indexer_client import IndexerClient
from hubble_exchange.models import (AsyncOrderBookDepthCallback,
                                    AsyncOrderStatusCallback,
                                    AsyncPlaceOrdersCallback,
                                    AsyncPositionCallback,
                                    AsyncSubscribeToOrderBookDepthCallback,
                                    ConfirmationMode, IOCOrder, LimitOrder,
                                    MarketFeedUpdate,
                                    OrderBookDepthUpdateResponse, OrderStatus,
                                    OrderStatusResponse, SignedOrder,
                                    TraderFeedUpdate, WebsocketResponse)
from hubble_exchange.order_book import OrderBookClient, TransactionMode
from hubble_exchange.utils import (add_0x_prefix, async_ttl_cache,
                                   float_to_scaled_int,
                                   get_address_from_private_key, get_new_salt,
                                   int_to_scaled_float,
                                   validate_limit_order_like)


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
        self.indexer_client = IndexerClient()
        self._private_key = private_key

        self.signed_order_ws_connection = None

    async def close_websocket(self):
        if self.signed_order_ws_connection:
            await self.signed_order_ws_connection.close()
            self.signed_order_ws_connection = None

        await self.web3_client.provider.disconnect()

    def set_transaction_mode(self, mode: TransactionMode):
        self.order_book_client.set_transaction_mode(mode)

    async def get_nonce(self):
        return await self.order_book_client.get_current_nonce()

    @async_ttl_cache(ttl=300)
    async def get_markets(self):
        return await self.order_book_client.get_markets()

    async def get_market_name(self, market_id):
        try:
            markets = await self.get_markets()
            return markets[market_id]
        except IndexError:
            raise ValueError(f"The given market {market_id} does not exist")

    async def get_order_book(self, market: int, callback: AsyncOrderBookDepthCallback):
        order_book_depth = await self.web3_client.eth.get_order_book_depth(market)
        return await callback(order_book_depth)

    async def get_margin_and_positions(self, callback: AsyncPositionCallback):
        response = await self.web3_client.eth.get_margin_and_positions(self.trader_address)
        return await callback(response)

    async def get_balance(self, callback):
        balance = await self.web3_client.eth.get_balance(self.trader_address)
        return await callback(int_to_scaled_float(balance, 18))

    async def get_limit_order_details(self, order_id: HexBytes, callback: AsyncOrderStatusCallback):
        """ Works only for open limit orders """
        response = await self.web3_client.eth.get_order_status(order_id.hex())
        return await callback(response)

    async def get_limit_order_status(self, order_id: HexBytes, callback):
        response = await self.order_book_client.get_limit_order_status(order_id)
        return await callback(response)

    async def get_signed_order_status(self, order_id: HexBytes, callback):
        status = None
        contract_response = await self.order_book_client.get_signed_order_status(order_id)
        try:
            if contract_response['status'] == OrderStatus.Invalid:
                # contract is not aware of the order, so check the rpc for details
                # if rpc also doesn't know about the order, then it's either invalid or it's expired
                api_response = await self.web3_client.eth.get_order_status(order_id.hex())
                api_status = api_response.status
                if api_status == "NEW":
                    status = OrderStatus.Placed.name
                elif api_status == "FILLED":
                    status = OrderStatus.Filled.name
                elif api_status == "CANCELED":
                    status = OrderStatus.Cancelled.name
                elif api_status == "REJECTED":
                    status = OrderStatus.Invalid.name
                elif api_status == "PARTIALLY_FILLED":
                    status = OrderStatus.PartiallyFilled.name
            else:
                status = contract_response['status'].name
        except OrderNotFound as e:
            # if order is not found in the rpc, but contract shows filled quantity, then it's partially filled
            if contract_response['filled_amount'] > 0:
                status = OrderStatus.PartiallyFilled.name
            else:
                status = OrderStatus.Invalid.name

        return await callback(status)

    async def get_open_orders(self, market_id: int, callback: AsyncOrderStatusCallback):
        response = await self.web3_client.eth.get_open_orders(self.trader_address, market_id)
        return await callback(response)

    async def get_trades(self, market, start_time, end_time, callback):
        if start_time is None or end_time is None:
            raise ValueError("Start and end time must be specified")

        response = await self.order_book_client.get_trades(self.trader_address, market, start_time, end_time)
        return await callback(response)

    async def place_limit_orders(self, orders: List[LimitOrder], wait_for_response: bool, callback: AsyncPlaceOrdersCallback, tx_options = None, mode=None):
        if len(orders) > 75:
            raise ValueError("Cannot place more than 75 orders at once")

        for order in orders:
            validate_limit_order_like(order)

            if order.post_only is None:
                raise ValueError("Order post only is not set")
            # trader and salt can be set automatically
            if order.trader in [None, "0x", ""]:
                order.trader = self.trader_address
            if order.salt in [None, 0]:
                order.salt = get_new_salt()

        order_ids = set()  # stores all the order ids
        for order in orders:
            order_hash = order.get_order_hash()
            order.id = order_hash
            order_ids.add(order_hash)  # add each order id to the set

        # if the response if requested then we'll have to wait for the transaction to be mined
        # This is because the receipt is generated only after the transaction is mined(accepted)
        if wait_for_response:
            mode = TransactionMode.wait_for_accept

        tx_response = await self.order_book_client.place_limit_orders(orders, tx_options, mode)
        tx_hash = tx_response.tx_hash
        if wait_for_response:
            receipt = tx_response.receipt
            if not receipt:
                receipt = await self.web3_client.eth.get_transaction_receipt(tx_hash)

            event_order_ids = set()  # stores order ids present in events
            response = []
            accepted_events = self.order_book_client.get_events_from_receipt(receipt, "OrderAccepted", "limit")
            for event in accepted_events:
                order_id = event.args.orderHash
                event_order_ids.add(add_0x_prefix(order_id.hex()))
                response.append({
                    "order_id": add_0x_prefix(order_id.hex()),
                    "success": True
                })

            rejected_events = self.order_book_client.get_events_from_receipt(receipt, "OrderRejected", "limit")
            for event in rejected_events:
                order_id = event.args.orderHash
                event_order_ids.add(add_0x_prefix(order_id.hex()))
                response.append({
                    "order_id": add_0x_prefix(order_id.hex()),
                    "success": False,
                    "error": event.args.err
                })

            # check for missing order ids; should never happen
            missing_order_ids = order_ids - event_order_ids
            for missing_id in missing_order_ids:
                response.append({
                    "order_id": missing_id,
                    "success": False,
                    "error": "Unknown error"
                })

            return await callback(response)
        else:
            return await callback(orders)

    async def place_ioc_orders(self, orders: List[IOCOrder], wait_for_response: bool, callback: AsyncPlaceOrdersCallback, tx_options = None, mode=None):
        if len(orders) > 75:
            raise ValueError("Cannot place more than 75 orders at once")

        for order in orders:
            validate_limit_order_like(order)

            if order.expire_at is None:
                raise ValueError("Order expiry is not set")

            # trader and salt can be set automatically
            if order.trader in [None, "0x", ""]:
                order.trader = self.trader_address
            if order.salt in [None, 0]:
                order.salt = get_new_salt()

        order_ids = set()  # stores all the order ids
        for order in orders:
            order_hash = order.get_order_hash()
            order.id = order_hash
            order_ids.add(order_hash)  # add each order id to the set

        # if the response if requested then we'll have to wait for the transaction to be mined
        # This is because the receipt is generated only after the transaction is mined(accepted)
        if wait_for_response:
            mode = TransactionMode.wait_for_accept

        tx_response = await self.order_book_client.place_ioc_orders(orders, tx_options, mode)
        tx_hash = tx_response.tx_hash
        if wait_for_response:
            receipt = tx_response.receipt
            if not receipt:
                receipt = await self.web3_client.eth.get_transaction_receipt(tx_hash)

            event_order_ids = set()  # stores order ids present in events
            response = []
            accepted_events = self.order_book_client.get_events_from_receipt(receipt, "OrderAccepted", "ioc")
            for event in accepted_events:
                order_id = event.args.orderHash
                event_order_ids.add(add_0x_prefix(order_id.hex()))
                response.append({
                    "order_id": add_0x_prefix(order_id.hex()),
                    "success": True
                })

            rejected_events = self.order_book_client.get_events_from_receipt(receipt, "OrderRejected", "ioc")
            for event in rejected_events:
                order_id = event.args.orderHash
                event_order_ids.add(add_0x_prefix(order_id.hex()))
                response.append({
                    "order_id": add_0x_prefix(order_id.hex()),
                    "success": False,
                    "error": event.args.err
                })

            # check for missing order ids; should never happen
            missing_order_ids = order_ids - event_order_ids
            for missing_id in missing_order_ids:
                response.append({
                    "order_id": missing_id,
                    "success": False,
                    "error": "Unknown error"
                })

            return await callback(response)
        else:
            return await callback(orders)

    def prepare_signed_order(self, amm_index: int, base_asset_quantity: float, price: float, reduce_only: bool, expiry_duration: int):
        order = SignedOrder(
            id=None, # type: ignore
            signature=None, # type: ignore
            amm_index=amm_index,
            trader=self.trader_address, # type: ignore
            base_asset_quantity=Web3.to_wei(abs(base_asset_quantity), 'ether') * int(math.copysign(1, base_asset_quantity)),
            price=Web3.to_wei(price, 'mwei'),
            salt=get_new_salt(),
            reduce_only=reduce_only,
            expire_at=int(time.time()) + expiry_duration)

        order.id = get_signed_order_hash(order)
        return order

    async def place_signed_orders(
        self, signed_orders: List[SignedOrder], callback: AsyncPlaceOrdersCallback
    ) -> None:
        if not self.signed_order_ws_connection:
            self.signed_order_ws_connection = await websockets.connect(self.websocket_endpoint)

        encoded_orders = []
        for signed_order in signed_orders:
            if not signed_order.trader:
                signed_order.trader = self.trader_address

            validate_limit_order_like(signed_order)
            if signed_order.expire_at is None:
                    raise ValueError("Order expiry is not set")

            encoded_order= encode_signed_order(signed_order, self._private_key)
            encoded_orders.append(encoded_order.hex())

        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "order_placeSignedOrders",
            "params": [json.dumps(encoded_orders)]
        }

        await self.signed_order_ws_connection.send(json.dumps(msg))

        message = await self.signed_order_ws_connection.recv()
        message_json = json.loads(message)
        orders = message_json.get('result', {}).get('orders', [])
        response = []
        for order in orders:
            order_response = {
                'success': order.get('success', False),
                'order_id': order.get('orderId', ''),
            }
            if order.get('error', ''):
                order_response['error'] = order['error']

            response.append(order_response)
        return await callback(response)


    async def cancel_limit_orders(self, orders: List[LimitOrder], wait_for_response: bool, callback, tx_options = None, mode=None):
        if len(orders) > 100:
            raise ValueError("Cannot cancel more than 100 orders at once")

        # if the response if requested then we'll have to wait for the transaction to be mined
        # This is because the receipt is generated only after the transaction is mined(accepted)
        if wait_for_response:
            mode = TransactionMode.wait_for_accept

        order_ids = set()  # stores all the order ids
        for order in orders:
            order_hash = order.get_order_hash()
            order.id = order_hash
            order_ids.add(order_hash)  # add each order id to the set

        tx_response = await self.order_book_client.cancel_orders(orders, tx_options, mode)
        tx_hash = tx_response.tx_hash

        if wait_for_response:
            receipt = tx_response.receipt
            if not receipt:
                receipt = await self.web3_client.eth.get_transaction_receipt(tx_hash)

            response = []
            event_order_ids = set()
            cancelled_events = self.order_book_client.get_events_from_receipt(receipt, "OrderCancelAccepted", "limit")
            for event in cancelled_events:
                event_order_ids.add(add_0x_prefix(event.args.orderHash.hex()))
                response.append({
                    "order_id": add_0x_prefix(event.args.orderHash.hex()),
                    "success": True
                })
            rejected_events = self.order_book_client.get_events_from_receipt(receipt, "OrderCancelRejected", "limit")
            for event in rejected_events:
                event_order_ids.add(add_0x_prefix(event.args.orderHash.hex()))
                response.append({
                    "order_id": add_0x_prefix(event.args.orderHash.hex()),
                    "success": False,
                    "error": event.args.err
                })

            missing_order_ids = order_ids - event_order_ids  # order ids not present in events
            for missing_id in missing_order_ids:
                response.append({
                    "order_id": missing_id,
                    "success": False,
                    "error": "Unknown error"
                })

            return await callback(response)
        else:
            return await callback(orders)

    async def cancel_order_by_id(self, order_id: HexBytes, wait_for_response: bool, callback, tx_options = None, mode=None):
        async def order_status_callback(response: OrderStatusResponse) -> LimitOrder:
            position_side_multiplier = 1 if response.positionSide == "LONG" else -1
            return LimitOrder(
                id=order_id,
                amm_index=response.symbol,
                trader=self.trader_address,
                base_asset_quantity=float_to_scaled_int(float(response.origQty) * position_side_multiplier, 18),
                price=float_to_scaled_int(float(response.price), 6),
                salt=int(response.salt),
                reduce_only=response.reduceOnly,
                post_only=response.postOnly,
            )
        order = await self.get_limit_order_details(order_id, order_status_callback)
        return await self.cancel_limit_orders([order], wait_for_response, callback, tx_options, mode)
    
    async def cancel_signed_orders(self, orders: List[SignedOrder], wait_for_response: bool, callback, tx_options = None, mode=None):
        if len(orders) > 100:
            raise ValueError("Cannot cancel more than 100 orders at once")

        # if the response if requested then we'll have to wait for the transaction to be mined
        # This is because the receipt is generated only after the transaction is mined(accepted)
        if wait_for_response:
            mode = TransactionMode.wait_for_accept

        order_ids = set()  # stores all the order ids
        for order in orders:
            if not order.signature:
                order.signature = get_signature(order, self._private_key)

            order.trader = self.trader_address
            order_hash = get_signed_order_hash(order)
            order.id = order_hash
            order_ids.add(order_hash)  # add each order id to the set

        tx_response = await self.order_book_client.cancel_signed_orders(orders, tx_options, mode)
        tx_hash = tx_response.tx_hash

        if wait_for_response:
            receipt = tx_response.receipt
            if not receipt:
                receipt = await self.web3_client.eth.get_transaction_receipt(tx_hash)

            response = []
            event_order_ids = set()
            cancelled_events = self.order_book_client.get_events_from_receipt(receipt, "OrderCancelAccepted", "signed")
            for event in cancelled_events:
                event_order_ids.add(add_0x_prefix(event.args.orderHash.hex()))
                response.append({
                    "order_id": add_0x_prefix(event.args.orderHash.hex()),
                    "success": True
                })
            rejected_events = self.order_book_client.get_events_from_receipt(receipt, "OrderCancelRejected", "signed")
            for event in rejected_events:
                event_order_ids.add(add_0x_prefix(event.args.orderHash.hex()))
                response.append({
                    "order_id": add_0x_prefix(event.args.orderHash.hex()),
                    "success": False,
                    "error": event.args.err
                })

            missing_order_ids = order_ids - event_order_ids  # order ids not present in events
            for missing_id in missing_order_ids:
                response.append({
                    "order_id": missing_id,
                    "success": False,
                    "error": "Unknown error"
                })

            return await callback(response)
        else:
            return await callback(orders)


    async def get_order_fills(self, order_id: str) -> List[Dict]:
        return await self.order_book_client.get_order_fills(order_id)

    async def get_candlesticks(self, market, interval, start_time, end_time):
        market_name = await self.get_market_name(market)
        return self.indexer_client.get_candles(market_name, interval, start_time, end_time)

    async def get_predicted_funding_rate(self, market):
        market_name = await self.get_market_name(market)
        return self.indexer_client.get_predicted_funding_rate(market_name)

    async def get_funding_rate(self, market, timestamp):
        market_name = await self.get_market_name(market)
        return self.indexer_client.get_historical_funding_rate(market_name, timestamp)

    async def get_open_interest(self, market, timestamp):
        market_name = await self.get_market_name(market)
        return self.indexer_client.get_historical_open_interest(market_name, timestamp)

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

    async def subscribe_to_order_book_depth_with_freq(
        self, market: int, callback: AsyncSubscribeToOrderBookDepthCallback, freq: str = "1s"
    ) -> None:
        async with websockets.connect(self.websocket_endpoint) as ws:
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "orderbook_subscribe",
                "params": ["streamDepthUpdateForMarketAndFreq", market, freq]
            }
            await ws.send(json.dumps(msg))

            async for message in ws:
                message_json = json.loads(message)

                if message_json.get('result'):
                    # ignore because it's a subscription confirmation with subscription id
                    continue
                response = WebsocketResponse(**message_json)
                if response.method and response.method == "orderbook_subscription":
                    response = OrderBookDepthUpdateResponse(
                        T=0,
                        symbol=response.params['result']['market'],
                        bids=[[str(int_to_scaled_float(int(price), 6)), str(int_to_scaled_float(int(qty), 18))] for price, qty in response.params['result']['longs'].items()],
                        asks=[[str(int_to_scaled_float(int(price), 6)), str(int_to_scaled_float(int(qty), 18))] for price, qty in response.params['result']['shorts'].items()],
                    )
                    await callback(ws, response)

    async def subscribe_to_trader_updates(
        self, update_type: ConfirmationMode, callback
    ) -> None:
        async with websockets.connect(self.websocket_endpoint) as ws:
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "trading_subscribe",
                "params": ["streamTraderUpdates", self.trader_address, update_type.value]
            }
            await ws.send(json.dumps(msg))

            async for message in ws:
                message_json = json.loads(message)
                if message_json.get('result'):
                    # ignore because it's a subscription confirmation with subscription id
                    continue
                response = WebsocketResponse(**message_json)
                if response.method and response.method == "trading_subscription":
                    response = TraderFeedUpdate(**response.params['result'])
                    await callback(ws, response)

    async def subscribe_to_market_updates(
        self, market, update_type: ConfirmationMode, callback
    ) -> None:
        async with websockets.connect(self.websocket_endpoint) as ws:
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "trading_subscribe",
                "params": ["streamMarketTrades", market, update_type.value]
            }
            await ws.send(json.dumps(msg))

            async for message in ws:
                message_json = json.loads(message)
                if message_json.get('result'):
                    # ignore because it's a subscription confirmation with subscription id
                    continue
                response = WebsocketResponse(**message_json)
                if response.method and response.method == "trading_subscription":
                    response = MarketFeedUpdate(**response.params['result'])
                    await callback(ws, response)
