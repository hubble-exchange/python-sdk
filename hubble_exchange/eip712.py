
from eip712_structs import Address, Boolean
from eip712_structs import EIP712Struct as EIP712StructBase
from eip712_structs import Int, Uint, make_domain
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from hexbytes import HexBytes
from web3 import Web3

from hubble_exchange.constants import CHAIN_ID, SignedOrderBookContractAddress
from hubble_exchange.models import SignedOrder as SignedOrderModel

domain = make_domain(name='Hubble', version="2.0", chainId=CHAIN_ID, verifyingContract=SignedOrderBookContractAddress)
domain_separator = HexBytes(domain.hash_struct())


class EIP712Struct(EIP712StructBase):
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.type_name = cls._name


class SignedOrder(EIP712Struct):
    _name = "Order"

    orderType = Uint(8)
    expireAt = Uint(256)
    ammIndex = Uint(256)
    trader = Address()
    baseAssetQuantity = Int(256)
    price = Uint(256)
    salt = Uint(256)
    reduceOnly = Boolean()
    postOnly = Boolean()


def _get_signed_order_hash(order: SignedOrder):
    message_hash = HexBytes(order.hash_struct())

    struct_hash = Web3.solidity_keccak(
        ['bytes2', 'bytes32', 'bytes32'],
        [b'\x19\x01', domain_separator, message_hash]
    )
    
    return HexBytes(struct_hash)


def get_signed_order_hash(signed_order: SignedOrderModel):
    order = SignedOrder(
        orderType=2,
        expireAt=signed_order.expire_at,
        ammIndex=signed_order.amm_index,
        trader=Web3.to_checksum_address(signed_order.trader),
        baseAssetQuantity=signed_order.base_asset_quantity,
        price=signed_order.price,
        salt=signed_order.salt,
        reduceOnly=signed_order.reduce_only,
        postOnly=True
    )

    message_hash = HexBytes(order.hash_struct())

    struct_hash = Web3.solidity_keccak(
        ['bytes2', 'bytes32', 'bytes32'],
        [b'\x19\x01', domain_separator, message_hash]
    )
    
    return HexBytes(struct_hash)


def encode_signed_order(signed_order: SignedOrderModel, private_key: str):
    order = SignedOrder(
        orderType=2,
        expireAt=signed_order.expire_at,
        ammIndex=signed_order.amm_index,
        trader=Web3.to_checksum_address(signed_order.trader),
        baseAssetQuantity=signed_order.base_asset_quantity,
        price=signed_order.price,
        salt=signed_order.salt,
        reduceOnly=signed_order.reduce_only,
        postOnly=True
    )

    signature = _get_signature(order, private_key)

    encoded_order = encode(
        ['uint8', 'uint256', 'uint256', 'address', 'int256', 'uint256', 'uint256', 'bool', 'bool', 'bytes'],
        [
            order.values['orderType'],
            order.values['expireAt'],
            order.values['ammIndex'],
            order.values['trader'],
            order.values['baseAssetQuantity'],
            order.values['price'],
            order.values['salt'],
            order.values['reduceOnly'],
            order.values['postOnly'],
            signature
        ]
    )

    signed_order.signature = signature

    return encoded_order


def get_signature(signed_order: SignedOrderModel, private_key: str):
    order = SignedOrder(
        orderType=2,
        expireAt=signed_order.expire_at,
        ammIndex=signed_order.amm_index,
        trader=Web3.to_checksum_address(signed_order.trader),
        baseAssetQuantity=signed_order.base_asset_quantity,
        price=signed_order.price,
        salt=signed_order.salt,
        reduceOnly=signed_order.reduce_only,
        postOnly=True
    )

    signature = _get_signature(order, private_key)

    return signature


def _get_signature(order: SignedOrder, private_key: str) -> HexBytes:
    types = order.to_message(domain)['types']
    types.pop('EIP712Domain', None)
    encoded_typed_data = encode_typed_data(domain.data_dict(), types, order.data_dict())
    signed_message = Account.sign_message(encoded_typed_data, private_key)

    return signed_message.signature
