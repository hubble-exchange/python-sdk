from eth_typing import Address

OrderBookContractAddress = Address("0x0300000000000000000000000000000000000000")
IOCBookContractAddress = Address("0x635c5F96989a4226953FE6361f12B96c5d50289b")
ClearingHouseContractAddress = Address("0x0300000000000000000000000000000000000002")

CHAIN_ID = 321123
MAX_GAS_LIMIT = 7_000_000  # 7 million
# TODO: change this as per hubblenext gas limit
GAS_PER_ORDER = 500_000  # 200k
