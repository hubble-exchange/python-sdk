import math
import random
import time

from eth_account import Account
from eth_typing import Address


def float_to_scaled_int(val: float, scale: int) -> int:
    big_float = math.floor(val * (10 ** scale))
    return int(big_float)


def get_address_from_private_key(private_key: str) -> Address:
    account = Account.from_key(private_key)
    return account.address

def get_new_salt() -> int:
    return int(str(time.time_ns()) + str(random.randint(0, 10000)))
