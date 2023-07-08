import json
import os
from enum import Enum
from typing import Any, Dict, List

from hexbytes import HexBytes

from hubble_exchange.constants import (CHAIN_ID, GAS_PER_ORDER, MAX_GAS_LIMIT,
                                       OrderBookContractAddress)
from hubble_exchange.eip712 import get_order_hash
from hubble_exchange.eth import HubblenetWeb3 as Web3
from hubble_exchange.eth import get_web3_client
from hubble_exchange.models import Order
from hubble_exchange.utils import get_address_from_private_key

# read abi from file
HERE = os.path.dirname(__file__)
with open(f"{HERE}/contract_abis/OrderBook.json", 'r') as abi_file:
    abi_str = abi_file.read()
    ABI = json.loads(abi_str)


class TransactionMode(Enum):
    no_wait = 0
    wait_for_accept = 1
    wait_for_head = 1


class OrderBookClient(object):
    def __init__(self, private_key: str):
        self._private_key = private_key
        self.public_address = get_address_from_private_key(private_key)

        self.web3_client = get_web3_client()
        self.order_book = self.web3_client.eth.contract(address=OrderBookContractAddress, abi=ABI)
        self.nonce = self.web3_client.eth.get_transaction_count(self.public_address)
        self.transaction_mode = TransactionMode.no_wait

    def set_transaction_mode(self, mode: TransactionMode):
        self.transaction_mode = mode

    def place_order(self, order: Order, custom_tx_options=None, mode=None) -> HexBytes:
        order_hash = get_order_hash(order)

        tx_options = {'gas': GAS_PER_ORDER}
        tx_options.update(custom_tx_options or {})

        self._send_orderbook_transaction("placeOrder", [order.to_dict()], tx_options, mode)
        return order_hash

    def place_orders(self, orders: List[Order], custom_tx_options=None, mode=None) -> List[Order]:
        """
        Place multiple orders at once. This is more efficient than placing them one by one.
        """
        place_order_payload = []

        for order in orders:
            order_hash = get_order_hash(order)
            order.id = order_hash
            place_order_payload.append(order.to_dict())

        tx_options = {'gas': min(GAS_PER_ORDER * len(orders), MAX_GAS_LIMIT)}
        tx_options.update(custom_tx_options or {})
        self._send_orderbook_transaction("placeOrders", [place_order_payload], tx_options, mode)
        return orders

    def cancel_orders(self, orders: list[Order], custom_tx_options=None, mode=None) -> None:
        cancel_order_payload = []
        for order in orders:
            cancel_order_payload.append(order.to_dict())

        tx_options = {'gas': min(GAS_PER_ORDER * len(orders), MAX_GAS_LIMIT)}
        tx_options.update(custom_tx_options or {})

        self._send_orderbook_transaction("cancelOrders", [cancel_order_payload], tx_options, mode)

    def _get_nonce(self) -> int:
        if self.nonce is None:
            self.nonce = self.web3_client.eth.get_transaction_count(self.public_address)
        else:
            self.nonce += 1
        return self.nonce - 1

    def _send_orderbook_transaction(self, method_name: str, args: List[Any], tx_options: Dict, mode: TransactionMode) -> HexBytes:
        if mode is None:
            mode = self.transaction_mode

        method = getattr(self.order_book.functions, method_name)
        nonce = self._get_nonce()
        tx_params = {
            'from': self.public_address,
            'chainId': CHAIN_ID,
            'maxFeePerGas': Web3.to_wei(60, 'gwei'),  # base + tip
            'maxPriorityFeePerGas': 0,  # tip
            'nonce': nonce,
        }
        if tx_options:
            tx_params.update(tx_options)

        transaction = method(*args).build_transaction(tx_params)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self._private_key)
        tx_hash = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        if mode == TransactionMode.wait_for_accept:
            self._wait_for_accept(tx_hash)
        elif mode == TransactionMode.wait_for_head:
            self._wait_for_head(tx_hash)

        return tx_hash

    def _wait_for_accept(self, tx_hash: HexBytes):
        self.web3_client.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=0.1)

    def _wait_for_head(self, tx_hash: HexBytes):
        self.web3_client.eth.wait_for_transaction_status(tx_hash, timeout=120, poll_latency=0.1)
