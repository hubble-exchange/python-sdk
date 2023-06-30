import json
import random
import time
import requests
import websocket
from typing import List, Callable, Any
from hexbytes import HexBytes
from hubble_exchange.models import (
    Order,
    OrderStatusResponse,
    OrderBookDepthResponse,
    GetPositionsResponse,
    OrderBookDepthUpdateResponse,
    WebsocketResponse,
)
from hubble_exchange.order_book import OrderBookClient
from hubble_exchange.utils import (
    get_rpc_endpoint,
    get_websocket_endpoint,
    float_to_scaled_int,
    get_address_from_private_key,
    get_new_salt,
)


class HubbleClient:
    def __init__(self, private_key: str):
        if not private_key:
            raise ValueError("Private key is not set")
        self.trader_address = get_address_from_private_key(private_key)
        if not self.trader_address:
            raise ValueError("Cannot determine trader address from private key")

        self.rpc_endpoint = get_rpc_endpoint()
        self.websocket_endpoint = get_websocket_endpoint()
        self.orderBookClient = OrderBookClient(private_key)

    def get_order_book(self, market: int) -> OrderBookDepthResponse:
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "trading_getTradingOrderBookDepth",
            "params": [market],
        }
        response = requests.post(self.rpc_endpoint, json=request_body)
        response_json = response.json()
        order_book = OrderBookDepthResponse(**response_json["result"])
        return order_book

    def get_margin_and_positions(self) -> GetPositionsResponse:
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "trading_getMarginAndPositions",
            "params": [self.trader_address],
        }
        response = requests.post(self.rpc_endpoint, json=request_body)
        response_json = response.json()
        positions = GetPositionsResponse(**response_json["result"])
        return positions

    def get_order_status(self, order_id: HexBytes) -> OrderStatusResponse:
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "trading_getOrderStatus",
            "params": [order_id.hex()],
        }
        response = requests.post(self.rpc_endpoint, json=request_body)
        response_json = response.json()
        order_status = OrderStatusResponse(**response_json["result"])
        return order_status

    def place_orders(self, orders: List[Order]) -> List[Order]:
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

        return self.orderBookClient.place_orders(orders)

    def place_single_order(
        self, market: int, base_asset_quantity: float, price: float, reduce_only: bool
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
        order_hash = self.orderBookClient.place_order(order)
        order.id = order_hash
        return order

    def cancel_orders(self, orders: List[Order]) -> None:
        self.orderBookClient.cancel_orders(orders)

    def cancel_order_by_id(self, order_id: HexBytes) -> None:
        order_status = self.get_order_status(order_id)
        order = Order(
            amm_index=order_status.Symbol,
            trader=self.trader_address,
            base_asset_quantity=float_to_scaled_int(order_status.OrigQty, 18),
            price=float_to_scaled_int(order_status.Price, 6),
            salt=order_status.Salt,
            reduce_only=order_status.ReduceOnly,
        )
        self.cancel_orders([order])

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
