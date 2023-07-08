
import os
from typing import Callable, Dict

from eth_typing import Address
from hexbytes import HexBytes
from web3 import HTTPProvider, Web3
from web3.eth.eth import Eth, Timeout
from web3.exceptions import TimeExhausted
from web3.main import Web3, get_default_modules
from web3.method import Method, default_root_munger
from web3.middleware import geth_poa_middleware
from web3.middleware.cache import construct_simple_cache_middleware
from web3.types import RPCEndpoint, _Hash32

from hubble_exchange.errors import OrderNotFound, TraderNotFound
from hubble_exchange.models import (GetPositionsResponse,
                                    OrderBookDepthResponse,
                                    OrderStatusResponse)


rpc_endpoint = ""
websocket_endpoint = ""


class HubblenetEth(Eth):
    _get_transaction_status: Method[Callable[[_Hash32], Dict]] = Method(RPCEndpoint("eth_getTransactionStatus"), mungers=[default_root_munger])
    _get_order_status: Method[Callable[[_Hash32], Dict]] = Method(RPCEndpoint("trading_getOrderStatus"), mungers=[default_root_munger])
    _get_margin_and_positions: Method[Callable[[Address], Dict]] = Method(RPCEndpoint("trading_getMarginAndPositions"), mungers=[default_root_munger])
    _get_order_book_depth: Method[Callable[[int], Dict]] = Method(RPCEndpoint("trading_getTradingOrderBookDepth"), mungers=[default_root_munger])

    def get_transaction_status(self, transaction_hash: _Hash32) -> Dict:
        return self._get_transaction_status(transaction_hash)

    def get_order_status(self, order_id: _Hash32) -> OrderStatusResponse:
        try:
            response = self._get_order_status(order_id)
            return OrderStatusResponse(**response)
        except ValueError as e:
            if len(e.args) > 0 and e.args[0].get('message', '') == "order not found":
                raise OrderNotFound()
            else:
                raise e

    def get_margin_and_positions(self, trader: Address) -> GetPositionsResponse:
        try:
            response = self._get_margin_and_positions(trader)
            return GetPositionsResponse(**response)
        except ValueError as e:
            if len(e.args) > 0 and e.args[0].get('message', '') == "trader not found":
                raise TraderNotFound()
            else:
                raise e

    def get_order_book_depth(self, market: int) -> OrderBookDepthResponse:
        response = self._get_order_book_depth(market)
        return OrderBookDepthResponse(**response)

    def wait_for_transaction_status(self, transaction_hash: HexBytes, timeout: float = 120, poll_latency: float = 0.1) -> Dict:
        try:
            with Timeout(timeout) as _timeout:
                while True:
                    try:
                        tx_status = self._get_transaction_status(transaction_hash.hex())
                    except:
                        tx_status = None
                    if tx_status is None or tx_status['status'] == "NOT_FOUND":
                        _timeout.sleep(poll_latency)
                        continue
                    else:
                        break
            return tx_status

        except Timeout:
            raise TimeExhausted(
                f"Transaction {HexBytes(transaction_hash) !r} is not in the chain "
                f"after {timeout} seconds"
            )


def get_web3_modules() -> Dict:
    modules = get_default_modules()
    modules["eth"] = HubblenetEth
    return modules

class HubblenetWeb3(Web3):
    eth: HubblenetEth


def get_rpc_endpoint() -> str:
    global rpc_endpoint
    if not rpc_endpoint:
        rpc_host = os.getenv("HUBBLE_RPC_HOST")
        if not rpc_host:
            raise ValueError("HUBBLE_RPC_HOST environment variable not set")
        blockchain_id = os.getenv("HUBBLE_BLOCKCHAIN_ID")
        if not blockchain_id:
            raise ValueError("HUBBLE_BLOCKCHAIN_ID environment variable not set")
        path = f"/ext/bc/{blockchain_id}/rpc"
        rpc_endpoint = f"https://{rpc_host}{path}"
    return rpc_endpoint


def get_websocket_endpoint() -> str:
    global websocket_endpoint
    if not websocket_endpoint:
        rpc_host = os.getenv("HUBBLE_RPC_HOST")
        if not rpc_host:
            raise ValueError("HUBBLE_RPC_HOST environment variable not set")
        blockchain_id = os.getenv("HUBBLE_BLOCKCHAIN_ID")
        if not blockchain_id:
            raise ValueError("HUBBLE_BLOCKCHAIN_ID environment variable not set")
        path = f"/ext/bc/{blockchain_id}/ws"
        websocket_endpoint = f"wss://{rpc_host}{path}"
    return websocket_endpoint


def get_web3_client() -> HubblenetWeb3:
    rpc_endpoint = get_rpc_endpoint()
    
    web3_client = HubblenetWeb3(HTTPProvider(rpc_endpoint), modules=get_web3_modules())
    web3_client.middleware_onion.inject(geth_poa_middleware, layer=0)

    # cache frequent eth_chainId calls
    cache_chain_id_middleware = construct_simple_cache_middleware()
    web3_client.middleware_onion.add(cache_chain_id_middleware, name="cache")
    return web3_client
