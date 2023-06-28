import os
import json

from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3
from web3.middleware import geth_poa_middleware

from models import Order, OrderStatusResponse, OrderBookDepthResponse
from utils import get_rpc_endpoint, get_address_from_private_key

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
        self.order_book = self.web3_client.eth.contract(address=OrderBookContractAddress, abi=ABI)

    def place_order(self, order: Order) -> HexBytes:
        order_hash_bytes = self.order_book.functions.getOrderHash(order.to_dict()).call()
        order_hash = HexBytes(order_hash_bytes)

        self._send_orderbook_transaction("placeOrder", [order.to_dict()])
        return order_hash


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

    def _send_orderbook_transaction(self, method_name, args) -> HexBytes:
        method = getattr(self.order_book.functions, method_name)
        transaction = method(*args).build_transaction({
            'from': self.public_address,
            'chainId': self.chain_id,
            # 'gasPrice': client.toWei('50', 'gwei'),
            'nonce': self._get_nonce(),
        })
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self._private_key)
        tx_hash = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash
