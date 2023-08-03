import json
import os
from enum import Enum
from typing import Any, Dict, List

from hexbytes import HexBytes
from web3.logs import DISCARD

from hubble_exchange.constants import (CHAIN_ID, GAS_PER_ORDER, MAX_GAS_LIMIT,
                                       ClearingHouseContractAddress,
                                       OrderBookContractAddress)
from hubble_exchange.eip712 import get_order_hash
from hubble_exchange.eth import get_async_web3_client, get_sync_web3_client
from hubble_exchange.models import Order
from hubble_exchange.utils import (get_address_from_private_key,
                                   int_to_scaled_float)

# read abi from file
HERE = os.path.dirname(__file__)
with open(f"{HERE}/contract_abis/OrderBook.json", 'r') as abi_file:
    abi_str = abi_file.read()
    ORDERBOOK_ABI = json.loads(abi_str)

with open(f"{HERE}/contract_abis/ClearingHouse.json", 'r') as abi_file:
    abi_str = abi_file.read()
    CLEARINGHOUSE_ABI = json.loads(abi_str)

with open(f"{HERE}/contract_abis/AMM.json", 'r') as abi_file:
    abi_str = abi_file.read()
    AMM_ABI = json.loads(abi_str)


class TransactionMode(Enum):
    no_wait = 0
    wait_for_head = 1
    wait_for_accept = 2


class OrderBookClient(object):
    def __init__(self, private_key: str):
        self._private_key = private_key
        self.public_address = get_address_from_private_key(private_key)

        self.web3_client = get_async_web3_client()
        self.order_book_contract = self.web3_client.eth.contract(address=OrderBookContractAddress, abi=ORDERBOOK_ABI)

        # get nonce from sync web3 client
        sync_web3 = get_sync_web3_client()
        self.nonce = sync_web3.eth.get_transaction_count(self.public_address)

        self.transaction_mode = TransactionMode.no_wait  # default

    def set_transaction_mode(self, mode: TransactionMode):
        self.transaction_mode = mode

    async def get_markets(self):
        clearing_house_contract = self.web3_client.eth.contract(address=ClearingHouseContractAddress, abi=CLEARINGHOUSE_ABI)
        amm_addresses = await clearing_house_contract.functions.getAMMs().call()

        markets = {}
        for i, amm_address in enumerate(amm_addresses):
            amm_contract = self.web3_client.eth.contract(address=amm_address, abi=AMM_ABI)
            name = await amm_contract.functions.name().call()
            markets[i] = name

        return markets

    async def place_order(self, order: Order, custom_tx_options=None, mode=None) -> HexBytes:
        order_hash = get_order_hash(order)

        tx_options = {'gas': GAS_PER_ORDER}
        tx_options.update(custom_tx_options or {})

        await self._send_orderbook_transaction("placeOrder", [order.to_dict()], tx_options, mode)
        return order_hash

    async def place_orders(self, orders: List[Order], custom_tx_options=None, mode=None):
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
        return await self._send_orderbook_transaction("placeOrders", [place_order_payload], tx_options, mode)

    async def cancel_orders(self, orders: list[Order], atomic, custom_tx_options=None, mode=None):
        cancel_order_payload = []
        for order in orders:
            cancel_order_payload.append(order.to_dict())

        tx_options = {'gas': min(GAS_PER_ORDER * len(orders), MAX_GAS_LIMIT)}
        tx_options.update(custom_tx_options or {})

        method_name = "cancelOrdersAtomic" if atomic else "cancelOrders"
        return await self._send_orderbook_transaction(method_name, [cancel_order_payload], tx_options, mode)

    async def get_order_fills(self, order_id: str) -> List[Dict]:
        orders_matched_events = await self.order_book_contract.events.OrderMatched().get_logs(
            {"orderHash": order_id},
            fromBlock='earliest',
        )

        fills = []
        for event in orders_matched_events:
            fills.append({
                "block_number": event.blockNumber,
                "transaction_hash": event.transactionHash,
                "timestamp": event.args.timestamp,
                "fill_amount": int_to_scaled_float(event.args.fillAmount, 18),
                "price": int_to_scaled_float(event.args.price, 6),
            })
        return fills

    def get_events_from_receipt(self, receipt, event_name):
        event = getattr(self.order_book_contract.events, event_name)
        return event().process_receipt(receipt, DISCARD)

    async def _get_nonce(self) -> int:
        if self.nonce is None:
            self.nonce = await self.web3_client.eth.get_transaction_count(self.public_address)
        else:
            self.nonce += 1
        return self.nonce - 1

    async def _send_orderbook_transaction(self, method_name: str, args: List[Any], tx_options: Dict, mode: TransactionMode) -> HexBytes:
        if mode is None:
            mode = self.transaction_mode

        method = getattr(self.order_book_contract.functions, method_name)
        nonce = await self._get_nonce()
        tx_params = {
            'from': self.public_address,
            'chainId': CHAIN_ID,
            'nonce': nonce,
        }
        if tx_options:
            tx_params.update(tx_options)

        transaction = await method(*args).build_transaction(tx_params)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self._private_key)
        tx_hash = await self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        if mode == TransactionMode.wait_for_accept:
            await self.web3_client.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=0.1)
        elif mode == TransactionMode.wait_for_head:
            await self.web3_client.eth.wait_for_transaction_status(tx_hash, timeout=120, poll_latency=0.1)

        return tx_hash
