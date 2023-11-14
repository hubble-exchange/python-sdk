
import asyncio
import os
from typing import Awaitable, Callable, Dict, List, Optional

from eth_typing import Address
from hexbytes import HexBytes
from web3 import AsyncHTTPProvider, AsyncWeb3, HTTPProvider, Web3
from web3.eth.async_eth import AsyncEth
from web3.exceptions import TimeExhausted
from web3.main import Web3, get_async_default_modules
from web3.method import Method, default_root_munger
from web3.middleware import (async_geth_poa_middleware,
                             construct_simple_cache_middleware,
                             geth_poa_middleware)
from web3.middleware.async_cache import _async_simple_cache_middleware
from web3.types import RPCEndpoint, TxParams, Wei, _Hash32

from hubble_exchange.errors import OrderNotFound, TraderNotFound
from hubble_exchange.models import (GetPositionsResponse, OpenOrder,
                                    OrderBookDepthResponse,
                                    OrderStatusResponse)
from hubble_exchange.constants import HTTP_PROTOCOL, WS_PROTOCOL

sync_web3_client = None
async_web3_client = None


class HubblenetEth(AsyncEth):
    _get_transaction_status: Method[Callable[[_Hash32], Awaitable[Dict]]] = Method(RPCEndpoint("eth_getTransactionStatus"), mungers=[default_root_munger])
    _get_order_status: Method[Callable[[_Hash32], Awaitable[Dict]]] = Method(RPCEndpoint("trading_getOrderStatus"), mungers=[default_root_munger])
    _get_margin_and_positions: Method[Callable[[Address], Awaitable[Dict]]] = Method(RPCEndpoint("trading_getMarginAndPositions"), mungers=[default_root_munger])
    _get_order_book_depth: Method[Callable[[int], Awaitable[Dict]]] = Method(RPCEndpoint("trading_getTradingOrderBookDepth"), mungers=[default_root_munger])
    _get_open_orders: Method[Callable[[Address, str], Awaitable[Dict]]] = Method(RPCEndpoint("orderbook_getOpenOrders"), mungers=[default_root_munger])

    async def get_order_status(self, order_id: _Hash32) -> OrderStatusResponse:
        try:
            response = await self._get_order_status(order_id)
            return OrderStatusResponse(**response)
        except ValueError as e:
            if len(e.args) > 0 and e.args[0].get('message', '') == "order not found":
                raise OrderNotFound()
            else:
                raise e

    async def get_margin_and_positions(self, trader: Address) -> GetPositionsResponse:
        try:
            response = await self._get_margin_and_positions(trader)
            return GetPositionsResponse(**response)
        except ValueError as e:
            if len(e.args) > 0 and e.args[0].get('message', '') == "trader not found":
                raise TraderNotFound()
            else:
                raise e

    async def get_order_book_depth(self, market: int) -> OrderBookDepthResponse:
        response = await self._get_order_book_depth(market)
        return OrderBookDepthResponse(**response)

    async def get_open_orders(self, trader:Address, market: int=None) -> List[OpenOrder]:
        if market is None:
            market_str = ""
        else:
            market_str = str(market)

        open_orders = []    
        response = await self._get_open_orders(trader, market_str)
        for order in response["Orders"]:
            open_orders.append(OpenOrder(**order))
        return open_orders

    async def wait_for_transaction_status(self, transaction_hash: HexBytes, timeout: float = 120, poll_latency: float = 0.1) -> Dict:
        async def _wait_for_status_with_timeout(
            _tx_hash: _Hash32, _poll_latency: float
        ) -> Dict:
            while True:
                try:
                    tx_status = await self._get_transaction_status(_tx_hash.hex())
                except:
                    tx_status = None
                if tx_status is None or tx_status['status'] == "NOT_FOUND":
                    await asyncio.sleep(_poll_latency)
                    continue
                else:
                    break
            return tx_status

        try:
            return await asyncio.wait_for(
                _wait_for_status_with_timeout(transaction_hash, poll_latency),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise TimeExhausted(
                f"Transaction {HexBytes(transaction_hash) !r} is not in the chain "
                f"after {timeout} seconds"
            )


class HubblenetWeb3(AsyncWeb3):
    eth: HubblenetEth


def get_web3_modules() -> Dict:
    modules = get_async_default_modules()
    modules["eth"] = HubblenetEth
    return modules


def get_async_web3_client() -> HubblenetWeb3:
    global async_web3_client
    if not async_web3_client:
        rpc_endpoint = get_rpc_endpoint()

        async_web3_client = HubblenetWeb3(AsyncHTTPProvider(rpc_endpoint), modules=get_web3_modules())
        async_web3_client.middleware_onion.inject(async_geth_poa_middleware, layer=0)

        # cache frequent eth_chainId calls
        async_web3_client.middleware_onion.add(_async_simple_cache_middleware, name="cache")

        # async_web3_client.eth.set_gas_price_strategy(rpc_gas_price_strategy)

    return async_web3_client


def get_sync_web3_client() -> Web3:
    global sync_web3_client
    if not sync_web3_client:
        rpc_endpoint = get_rpc_endpoint()

        sync_web3_client = Web3(HTTPProvider(rpc_endpoint))
        sync_web3_client.middleware_onion.inject(geth_poa_middleware, layer=0)

        sync_web3_client.middleware_onion.add(construct_simple_cache_middleware(), name="cache")

    return sync_web3_client


def get_rpc_endpoint() -> str:
    rpc_endpoint = os.getenv("HUBBLE_RPC")
    if not rpc_endpoint:
        raise ValueError("HUBBLE_RPC environment variable not set")
    return rpc_endpoint


def get_websocket_endpoint() -> str:
    ws_rpc_endpoint = os.getenv("HUBBLE_WS_RPC")
    if not ws_rpc_endpoint:
        raise ValueError("HUBBLE_WS_RPC environment variable not set")
    return ws_rpc_endpoint
