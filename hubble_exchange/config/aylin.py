from eth_typing import Address
from web3 import Web3

__all__ = ['CHAIN_ID', 'MAX_GAS_LIMIT', 'GAS_PER_ORDER', 'OrderBookContractAddress', 'IOCBookContractAddress',
           'ClearingHouseContractAddress', 'min_quantity', 'price_precision', 'HTTP_PROTOCOL', 'WS_PROTOCOL']

OrderBookContractAddress = Web3.to_checksum_address(Address("0x03000000000000000000000000000000000000b0"))
LimitOrderBookContractAddress = Web3.to_checksum_address(Address("0x03000000000000000000000000000000000000b3"))
IOCBookContractAddress = Web3.to_checksum_address(Address("0x03000000000000000000000000000000000000b4"))
ClearingHouseContractAddress = Web3.to_checksum_address(Address("0x03000000000000000000000000000000000000b2"))

CHAIN_ID = 486
MAX_GAS_LIMIT = 7_000_000  # 7 million
GAS_PER_ORDER = 300_000  # 300k

min_quantity = {
    0: 0.01,
    1: 1,
    2: 10,
}

price_precision = {
    0: 2,
    1: 3,
    2: 4,
}

HTTP_PROTOCOL = "https"
WS_PROTOCOL = "wss"

allowed_candle_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w", "1M"]
