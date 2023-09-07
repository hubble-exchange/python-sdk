from eth_typing import Address

__all__ = ['CHAIN_ID', 'MAX_GAS_LIMIT', 'GAS_PER_ORDER', 'OrderBookContractAddress', 'IOCBookContractAddress',
           'ClearingHouseContractAddress', 'min_quantity', 'price_precision', 'HTTP_PROTOCOL', 'WS_PROTOCOL']


OrderBookContractAddress = Address("0x0300000000000000000000000000000000000000")
IOCBookContractAddress = Address("0x635c5F96989a4226953FE6361f12B96c5d50289b")
ClearingHouseContractAddress = Address("0x0300000000000000000000000000000000000002")

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
