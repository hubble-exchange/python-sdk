import concurrent.futures
import json
import os

from eth_typing import Address
from hexbytes import HexBytes
from typing import List, Dict, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.middleware.cache import construct_simple_cache_middleware

from hubble_exchange.models import Order
from hubble_exchange.utils import get_rpc_endpoint, get_address_from_private_key

MAX_GAS_LIMIT = 15_000_000  # 15 million
OrderBookContractAddress = Address("0x0300000000000000000000000000000000000000")

# read abi from file
dir_ = os.path.dirname(__file__)
with open(f"{dir_}/contract_abis/OrderBook.json", 'r') as abi_file:
    abi_str = abi_file.read()
    ABI = json.loads(abi_str)


class OrderBookClient(object):
    def __init__(self, private_key: str):
        self.rpc_endpoint = get_rpc_endpoint()
        self._private_key = private_key
        self.public_address = get_address_from_private_key(private_key)
        self.nonce = None
        self.chain_id = 321123

        self.web3_client = Web3(Web3.HTTPProvider(self.rpc_endpoint))
        self.web3_client.middleware_onion.inject(geth_poa_middleware, layer=0)

        # cache frequent eth_chainId calls
        cache_chain_id_middleware = construct_simple_cache_middleware()
        self.web3_client.middleware_onion.add(cache_chain_id_middleware, name="cache")

        self.order_book = self.web3_client.eth.contract(address=OrderBookContractAddress, abi=ABI)

    def place_order(self, order: Order) -> HexBytes:
        order_hash = self._get_order_hash(order)

        self._send_orderbook_transaction("placeOrder", [order.to_dict()], {'gas': 200_000})
        return order_hash

    def place_orders(self, orders: List[Order]) -> List[Order]:
        """
        Place multiple orders at once. This is more efficient than placing them one by one.
        """
        place_order_payload = []

        # get order hashes concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            order_hashes = list(executor.map(self._get_order_hash, orders))

        for order, order_hash_bytes in zip(orders, order_hashes):
            order_hash = HexBytes(order_hash_bytes)
            place_order_payload.append(order.to_dict())
            order.id = order_hash

        self._send_orderbook_transaction("placeOrders", [place_order_payload], {'gas': min(200_000 * len(orders), MAX_GAS_LIMIT)})
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
    
    def _get_order_hash(self, order: Order) -> HexBytes:
        order_hash_bytes = self.order_book.functions.getOrderHash(order.to_dict()).call()
        return HexBytes(order_hash_bytes)

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
