from eip712_structs import Address, Boolean
from eip712_structs import EIP712Struct as EIP712StructBase
from eip712_structs import Int, Uint, make_domain
from eth_utils import keccak
from hexbytes import HexBytes

from hubble_exchange.constants import (CHAIN_ID, IOCBookContractAddress,
                                       OrderBookContractAddress)
from hubble_exchange.models import IOCOrder as IOCOrderModel
from hubble_exchange.models import LimitOrder as LimitOrderModel

limit_order_domain = make_domain(name='Hubble', version="2.0", chainId=CHAIN_ID, verifyingContract=OrderBookContractAddress)
limit_order_domain_hash = HexBytes(limit_order_domain.hash_struct())

ioc_order_domain = make_domain(name='Hubble', version="2.0", chainId=CHAIN_ID, verifyingContract=IOCBookContractAddress)
ioc_order_domain_hash = HexBytes(ioc_order_domain.hash_struct())


class EIP712Struct(EIP712StructBase):
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.type_name = cls._name


class LimitOrder(EIP712Struct):
    _name = "Order"

    ammIndex = Uint(256)
    trader = Address()
    baseAssetQuantity = Int(256)
    price = Uint(256)
    salt = Uint(256)
    reduceOnly = Boolean()


class IOCOrder(EIP712Struct):
    _name = "IOCOrder"

    orderType = Uint(8)
    expireAt = Uint(256)
    ammIndex = Uint(256)
    trader = Address()
    baseAssetQuantity = Int(256)
    price = Uint(256)
    salt = Uint(256)
    reduceOnly = Boolean()


def get_limit_order_hash(order: LimitOrderModel) -> HexBytes:
    order_struct = LimitOrder(
        ammIndex=order.amm_index,
        trader=order.trader,
        baseAssetQuantity=order.base_asset_quantity,
        price=order.price,
        salt=order.salt,
        reduceOnly=order.reduce_only,
    )

    order_struct_hash = HexBytes(order_struct.hash_struct())
    order_hash_bytes = b'\x19\x01' + limit_order_domain_hash + order_struct_hash
    order_hash = HexBytes(keccak(order_hash_bytes))
    return order_hash


def get_ioc_order_hash(order: IOCOrderModel) -> HexBytes:
    order_struct = IOCOrder(
        orderType=1,
        expireAt=order.expire_at,
        ammIndex=order.amm_index,
        trader=order.trader,
        baseAssetQuantity=order.base_asset_quantity,
        price=order.price,
        salt=order.salt,
        reduceOnly=order.reduce_only,
    )

    order_struct_hash = HexBytes(order_struct.hash_struct())
    order_hash_bytes = b'\x19\x01' + ioc_order_domain_hash + order_struct_hash
    order_hash = HexBytes(keccak(order_hash_bytes))
    return order_hash
