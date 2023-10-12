import functools
import random
import time
from decimal import Decimal, getcontext

from eth_account import Account
from eth_typing import Address
from eth_utils.hexadecimal import add_0x_prefix as add_0x_prefix_eth_utils
from hexbytes import HexBytes

from hubble_exchange.constants import get_minimum_quantity, get_price_precision

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


def get_precision(value: float) -> int:
    # Convert float to string
    value_str = str(value)

    # Check if there's a decimal point in the string representation
    if '.' not in value_str:
        return 0

    # Split at the decimal point and return the length of the second part
    return len(value_str.split('.')[1])


def validate_limit_order_like(order):
    if order.amm_index is None:
        raise ValueError("Order AMM index is not set")
    if order.base_asset_quantity is None:
        raise ValueError("Order base asset quantity is not set")
    if order.price is None:
        raise ValueError("Order price is not set")
    if order.reduce_only is None:
        raise ValueError("Order reduce only is not set")

    min_quantity = get_minimum_quantity(order.amm_index)
    scaled_min_quantity = float_to_scaled_int(min_quantity, 18)
    if not is_multiple(order.base_asset_quantity, scaled_min_quantity):
        unscaled_order_size = int_to_scaled_float(order.base_asset_quantity, 18)
        raise ValueError(f"Order quantity {unscaled_order_size} is not a multiple of minimum quantity {min_quantity}")

    allowed_price_precision = get_price_precision(order.amm_index)
    price = int_to_scaled_float(order.price, 6)
    if get_precision(price) > allowed_price_precision:
        raise ValueError(f"Decimal precision of order price {price} is greater than allowed precision {allowed_price_precision}")


def is_multiple(a, b, tolerance=1e-9):
    remainder = a % b
    return abs(remainder) < tolerance or abs(remainder - b) < tolerance


def async_ttl_cache(ttl=300):
    def decorator(func):
        cache = {}
        cache_expiry = {}

        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            cache_key = str(args) + str(kwargs)
            current_time = time.time()

            if cache_key in cache and (current_time - cache_expiry[cache_key] < ttl):
                return cache[cache_key]

            result = await func(*args, **kwargs)
            cache[cache_key] = result
            cache_expiry[cache_key] = current_time

            return result

        return wrapped

    return decorator
