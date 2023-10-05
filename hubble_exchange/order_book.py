import json
import os
from typing import Any, Dict, List

from eth_typing import Address
from hexbytes import HexBytes
from web3.contract.async_contract import AsyncContractFunction
from web3.logs import DISCARD

from hubble_exchange.constants import (CHAIN_ID, GAS_PER_ORDER, MAX_GAS_LIMIT,
                                       ClearingHouseContractAddress,
                                       IOCBookContractAddress,
                                       LimitOrderBookContractAddress,
                                       OrderBookContractAddress)
from hubble_exchange.eth import get_async_web3_client, get_sync_web3_client
from hubble_exchange.models import (ExecutionMode, IOCOrder, LimitOrder,
                                    OrderStatus, Trade, TransactionMode)
from hubble_exchange.utils import (get_address_from_private_key,
                                   int_to_scaled_float)

# read abi from file
HERE = os.path.dirname(__file__)
with open(f"{HERE}/contract_abis/OrderBook.json", 'r') as abi_file:
    abi_str = abi_file.read()
    ORDERBOOK_ABI = json.loads(abi_str)

with open(f"{HERE}/contract_abis/LimitOrderBook.json", 'r') as abi_file:
    abi_str = abi_file.read()
    LIMIT_ORDERBOOK_ABI = json.loads(abi_str)

with open(f"{HERE}/contract_abis/ImmediateOrCancelOrders.json", 'r') as abi_file:
    abi_str = abi_file.read()
    IOC_ORDERBOOK_ABI = json.loads(abi_str)

with open(f"{HERE}/contract_abis/ClearingHouse.json", 'r') as abi_file:
    abi_str = abi_file.read()
    CLEARINGHOUSE_ABI = json.loads(abi_str)

with open(f"{HERE}/contract_abis/AMM.json", 'r') as abi_file:
    abi_str = abi_file.read()
    AMM_ABI = json.loads(abi_str)


class OrderBookClient(object):
    def __init__(self, private_key: str):
        self._private_key = private_key
        self.public_address = get_address_from_private_key(private_key)

        self.web3_client = get_async_web3_client()
        self.order_book_contract = self.web3_client.eth.contract(address=OrderBookContractAddress, abi=ORDERBOOK_ABI)
        self.limit_order_book_contract = self.web3_client.eth.contract(address=LimitOrderBookContractAddress, abi=LIMIT_ORDERBOOK_ABI)
        self.ioc_order_book_contract = self.web3_client.eth.contract(address=IOCBookContractAddress, abi=IOC_ORDERBOOK_ABI)
        self.clearing_house_contract = self.web3_client.eth.contract(address=ClearingHouseContractAddress, abi=CLEARINGHOUSE_ABI)

        # get nonce from sync web3 client
        sync_web3 = get_sync_web3_client()
        self.nonce = sync_web3.eth.get_transaction_count(self.public_address)

        self.transaction_mode = TransactionMode.no_wait  # default

    def set_transaction_mode(self, mode: TransactionMode):
        self.transaction_mode = mode

    async def get_markets(self):
        amm_addresses = await self.clearing_house_contract.functions.getAMMs().call()

        markets = {}
        for i, amm_address in enumerate(amm_addresses):
            amm_contract = self.web3_client.eth.contract(address=amm_address, abi=AMM_ABI)
            name = await amm_contract.functions.name().call()
            markets[i] = name

        return markets

    async def get_limit_order_status(self, order_id: HexBytes):
        response = await self.limit_order_book_contract.functions.orderStatus(order_id).call()
        status = response[3]
        filled_amount = response[1]
        if status == OrderStatus.Placed.value and filled_amount > 0:
            status = OrderStatus.PartiallyFilled.value
        return OrderStatus(status).name

    async def place_limit_orders(self, orders: List[LimitOrder], custom_tx_options=None, mode=None):
        """
        Place limit orders
        """
        place_order_payload = []

        for order in orders:
            place_order_payload.append(order.to_dict())

        tx_options = {'gas': min(GAS_PER_ORDER * len(orders), MAX_GAS_LIMIT)}
        tx_options.update(custom_tx_options or {})
        method = getattr(self.limit_order_book_contract.functions, "placeOrders")
        return await self._send_transaction(method, [place_order_payload], tx_options, mode)

    async def place_ioc_orders(self, orders: List[IOCOrder], custom_tx_options=None, mode=None):
        """
        Place ioc orders
        """
        place_order_payload = []

        for order in orders:
            place_order_payload.append(order.to_dict())

        tx_options = {'gas': min(GAS_PER_ORDER * len(orders), MAX_GAS_LIMIT)}
        tx_options.update(custom_tx_options or {})
        method = getattr(self.ioc_order_book_contract.functions, "placeOrders")
        return await self._send_transaction(method, [place_order_payload], tx_options, mode)

    async def cancel_orders(self, orders: list[LimitOrder], custom_tx_options=None, mode=None):
        cancel_order_payload = []
        for order in orders:
            cancel_order_payload.append(order.to_dict())

        tx_options = {'gas': min(GAS_PER_ORDER * len(orders), MAX_GAS_LIMIT)}
        tx_options.update(custom_tx_options or {})

        method = getattr(self.limit_order_book_contract.functions, "cancelOrders")
        return await self._send_transaction(method, [cancel_order_payload], tx_options, mode)

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

    async def get_trades(self, trader:Address, market:int, start_time:int, end_time:int) -> List[Dict]:
        query = {"trader": trader}
        if market is not None:
            query["idx"] = market

        latest_block_number = await self.web3_client.eth.get_block_number()

        # iterate in chunks till event.timestamp <= start_time
        CHUNK_SIZE = 20000
        trades = []
        to_block = latest_block_number
        while True:
            if to_block <= 0:
                break
            from_block = max(to_block - CHUNK_SIZE - 1, 0)  # because from and to blocks both are inclusive
            trades_events = await self.clearing_house_contract.events.PositionModified().get_logs(
                query,
                fromBlock=from_block,
                toBlock=to_block,
            )

            # break early if even the first event is after end_time
            if len(trades_events) == 0 or trades_events[0].args.timestamp > end_time:
                # get the earliest block and check its timestamp; exit early if it's less than start_time
                earliest_block = await self.web3_client.eth.get_block(from_block)
                if earliest_block.timestamp < start_time:
                    break

                to_block -= CHUNK_SIZE
                continue

            # reversed because we want the response to be from latest to earliest
            for event in reversed(trades_events):
                if event.args.timestamp < start_time:
                    break
                if event.args.timestamp <= end_time:
                    trades.append(Trade(
                        BlockNumber=event.blockNumber,
                        TransactionHash=event.transactionHash,
                        Market=event.args.idx,
                        Timestamp=event.args.timestamp,
                        TradedAmount=int_to_scaled_float(event.args.baseAsset, 18),
                        Price=int_to_scaled_float(event.args.price, 6),
                        RealizedPnl=int_to_scaled_float(event.args.realizedPnl, 6),
                        OpenNotional=int_to_scaled_float(event.args.openNotional, 18),
                        ExecutionMode=ExecutionMode(event.args.mode).name,
                    ))

            to_block -= CHUNK_SIZE
            continue

        return trades

    def get_events_from_receipt(self, receipt, event_name, contract_name=None):
        if contract_name is None:
            contract = self.order_book_contract
        if contract_name == "ioc":
            contract = self.ioc_order_book_contract
        if contract_name == "limit":
            contract = self.limit_order_book_contract
        event = getattr(contract.events, event_name)
        return event().process_receipt(receipt, DISCARD)

    async def get_current_nonce(self) -> int:
        return await self.web3_client.eth.get_transaction_count(self.public_address)

    async def _get_nonce(self) -> int:
        if self.nonce is None:
            self.nonce = await self.web3_client.eth.get_transaction_count(self.public_address)
        else:
            self.nonce += 1
        return self.nonce - 1

    async def _send_transaction(self, method: AsyncContractFunction, args: List[Any], tx_options: Dict, mode: TransactionMode) -> HexBytes:
        if mode is None:
            mode = self.transaction_mode

        nonce = await self._get_nonce()
        tx_params = {
            'from': self.public_address,
            'chainId': CHAIN_ID,
            'nonce': nonce,
            # "maxFeePerGas": web3.Web3.to_wei(90, 'gwei'),
            # "maxPriorityFeePerGas": web3.Web3.to_wei(30, 'gwei'),
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
