from eip712_structs import (Address, Boolean, EIP712Struct, Int, Uint,
                            make_domain)
from eth_utils import keccak
from hexbytes import HexBytes

from hubble_exchange.constants import CHAIN_ID, OrderBookContractAddress
from hubble_exchange.models import Order as OrderModel

domain = make_domain(name='Hubble', version="2.0", chainId=CHAIN_ID, verifyingContract=OrderBookContractAddress)
domain_hash = HexBytes(domain.hash_struct())


# Class name must match the struct name in the solidity contract
class Order(EIP712Struct):
    ammIndex = Uint(256)
    trader = Address()
    baseAssetQuantity = Int(256)
    price = Uint(256)
    salt = Uint(256)
    reduceOnly = Boolean()


def get_order_hash(order: OrderModel) -> HexBytes:
    order_struct = Order(
        ammIndex=order.amm_index,
        trader=order.trader,
        baseAssetQuantity=order.base_asset_quantity,
        price=order.price,
        salt=order.salt,
        reduceOnly=order.reduce_only,
    )

    order_struct_hash = HexBytes(order_struct.hash_struct())
    order_hash_bytes = b'\x19\x01' + domain_hash + order_struct_hash
    order_hash = HexBytes(keccak(order_hash_bytes))
    return order_hash
