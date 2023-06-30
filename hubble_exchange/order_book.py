import concurrent.futures
import json
import os

from hexbytes import HexBytes
from typing import List, Dict, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.middleware.cache import construct_simple_cache_middleware

from hubble_exchange.constants import OrderBookContractAddress, MAX_GAS_LIMIT, CHAIN_ID, GAS_PER_ORDER
from hubble_exchange.eip712 import get_order_hash
from hubble_exchange.models import Order
from hubble_exchange.utils import get_rpc_endpoint, get_address_from_private_key

# read abi from file
HERE = os.path.dirname(__file__)
with open(f"{HERE}/contract_abis/OrderBook.json", 'r') as abi_file:
    abi_str = abi_file.read()
    ABI = json.loads(abi_str)


class OrderBookClient(object):
    def __init__(self, private_key: str):
        self.rpc_endpoint = get_rpc_endpoint()
        self._private_key = private_key
        self.public_address = get_address_from_private_key(private_key)
        self.nonce = None
        self.chain_id = CHAIN_ID

        self.web3_client = Web3(Web3.HTTPProvider(self.rpc_endpoint))
        self.web3_client.middleware_onion.inject(geth_poa_middleware, layer=0)

        # cache frequent eth_chainId calls
        cache_chain_id_middleware = construct_simple_cache_middleware()
        self.web3_client.middleware_onion.add(cache_chain_id_middleware, name="cache")

        self.order_book = self.web3_client.eth.contract(address=OrderBookContractAddress, abi=ABI)

    def place_order(self, order: Order) -> HexBytes:
        order_hash = get_order_hash(order)

        self._send_orderbook_transaction("placeOrder", [order.to_dict()], {'gas': GAS_PER_ORDER})
        return order_hash

    def place_orders(self, orders: List[Order]) -> List[Order]:
        """
        Place multiple orders at once. This is more efficient than placing them one by one.
        """
        place_order_payload = []

        for order in orders:
            order_hash = get_order_hash(order)
            order.id = order_hash
            place_order_payload.append(order.to_dict())

        self._send_orderbook_transaction("placeOrders", [place_order_payload], {'gas': min(GAS_PER_ORDER * len(orders), MAX_GAS_LIMIT)})
        return orders


    def cancel_orders(self, orders: list[Order]) -> None:
        cancel_order_payload = []
        for order in orders:
            cancel_order_payload.append(order.to_dict())
        self._send_orderbook_transaction("cancelOrders", [cancel_order_payload])


    def _get_nonce(self) -> int:
        if self.nonce is None:
            self.nonce = self.web3_client.eth.get_transaction_count(self.public_address)
        else:
            self.nonce += 1
        return self.nonce

    def _send_orderbook_transaction(self, method_name: str, args: List[Any], tx_options: Dict = None) -> HexBytes:
        method = getattr(self.order_book.functions, method_name)
        nonce = self._get_nonce()
        tx_params = {
            'from': self.public_address,
            'chainId': self.chain_id,
            'maxFeePerGas': Web3.to_wei(60, 'gwei'),
            'maxPriorityFeePerGas': 0,
            'nonce': nonce,
        }
        if tx_options:
            tx_params.update(tx_options)

        transaction = method(*args).build_transaction(tx_params)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self._private_key)
        tx_hash = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash
