import random
import time
from decimal import Decimal, getcontext

from eth_account import Account
from eth_typing import Address
from eth_utils.hexadecimal import add_0x_prefix as add_0x_prefix_eth_utils
from hexbytes import HexBytes

# Set the precision higher than default to handle larger numbers without issues.
getcontext().prec = 50


def float_to_scaled_int(val: float, scale: int) -> int:
    scaled_value = Decimal(str(val)) * (Decimal('10') ** Decimal(scale))
    return int(scaled_value)


def int_to_scaled_float(val: int, scale: int) -> float:
    return float(Decimal(val) / (Decimal('10') ** Decimal(scale)))


def get_address_from_private_key(private_key: str) -> Address:
    account = Account.from_key(private_key)
    return account.address

def get_new_salt() -> int:
    return int(str(time.time_ns()) + str(random.randint(0, 10000)))


def add_0x_prefix(value: str) -> HexBytes:
    return HexBytes(add_0x_prefix_eth_utils(value))
