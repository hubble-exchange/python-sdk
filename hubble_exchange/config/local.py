from eth_typing import Address

__all__ = ['CHAIN_ID', 'MAX_GAS_LIMIT', 'GAS_PER_ORDER', 'OrderBookContractAddress', 'IOCBookContractAddress',
           'ClearingHouseContractAddress', 'min_quantity', 'price_precision', 'HTTP_PROTOCOL', 'WS_PROTOCOL']


OrderBookContractAddress = Address("0x03000000000000000000000000000000000000b0")
LimitOrderBookContractAddress = Address("0x03000000000000000000000000000000000000b3")
IOCBookContractAddress = Address("0x03000000000000000000000000000000000000b4")
ClearingHouseContractAddress = Address("0x03000000000000000000000000000000000000b2")

CHAIN_ID = 321123
MAX_GAS_LIMIT = 7_000_000  # 7 million
GAS_PER_ORDER = 300_000  # 300k

min_quantity = {
    0: 0.01,
}

price_precision = {
    0: 6,
}

HTTP_PROTOCOL = "http"
WS_PROTOCOL = "ws"
