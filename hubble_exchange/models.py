import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Coroutine, Dict, List

from eth_typing import Address
from hexbytes import HexBytes
from typing_extensions import Protocol
from web3 import Web3

from hubble_exchange.utils import float_to_scaled_int, get_new_salt


@dataclass
class LimitOrder:
    id: HexBytes
    amm_index: int
    trader: Address
    base_asset_quantity: int
    price: int
    salt: int
    reduce_only: bool
    post_only: bool

    def to_dict(self):
        return {
            "ammIndex": self.amm_index,
            "trader": Web3.to_checksum_address(self.trader),
            "baseAssetQuantity": self.base_asset_quantity,
            "price": self.price,
            "salt": self.salt,
            "reduceOnly": self.reduce_only,
            "postOnly": self.post_only,
        }

    @classmethod
    def new(cls, amm_index: int, base_asset_quantity: float, price: float, reduce_only: bool, post_only: bool):
        """
        Create a new order with a random salt and no ID or trader. This can be used for placing
        multiple orders at once.
        """
        return cls(
            id=None, # type: ignore
            amm_index=amm_index,
            trader=None, # type: ignore
            base_asset_quantity=float_to_scaled_int(base_asset_quantity, 18),
            price=float_to_scaled_int(price, 6),
            salt=get_new_salt(),
            reduce_only=reduce_only,
            post_only=post_only)

    def get_order_hash(self):
        """
        Implements the same logic as the contract's getOrderHash function  - keccak256(abi.encode(order))
        It's converting each field to bytes and then concatenating them together instead of using Web3.solidity_keccak function
        because it was giving incorrect results.
        One important part is to pad all the fields to 32 bytes
        """
        packed_data = (
            int_to_bytes(self.amm_index) +
            Web3.to_bytes(hexstr=self.trader).rjust(32, b'\0') +
            int_to_bytes(self.base_asset_quantity) +
            int_to_bytes(self.price) +
            int_to_bytes(self.salt) +
            (b'\x01' if self.reduce_only else b'\x00').rjust(32, b'\0') +
            (b'\x01' if self.post_only else b'\x00').rjust(32, b'\0')
        )
        return Web3.keccak(packed_data)


@dataclass
class IOCOrder:
    id: HexBytes
    amm_index: int
    trader: Address
    base_asset_quantity: int
    price: int
    salt: int
    reduce_only: bool
    expire_at: int

    def to_dict(self):
        return {
            "ammIndex": self.amm_index,
            "trader": self.trader,
            "baseAssetQuantity": self.base_asset_quantity,
            "price": self.price,
            "salt": self.salt,
            "reduceOnly": self.reduce_only,
            "expireAt": self.expire_at,
            "orderType": 1,  # hardcoded type = 1 for ioc orders
        }

    @classmethod
    def new(cls, amm_index: int, base_asset_quantity: float, price: float, reduce_only: bool, expiry_duration: int):
        """
        Create a new order with a random salt and no ID or trader. This can be used for placing
        multiple orders at once.
        """
        return cls(
            id=None, # type: ignore
            amm_index=amm_index,
            trader=None, # type: ignore
            base_asset_quantity=float_to_scaled_int(base_asset_quantity, 18),
            price=float_to_scaled_int(price, 6),
            salt=get_new_salt(),
            reduce_only=reduce_only,
            expire_at=int(time.time()) + expiry_duration)

    def get_order_hash(self):
        """
        Implements the same logic as the contract's getOrderHash function  - keccak256(abi.encode(order))
        It's converting each field to bytes and then concatenating them together instead of using Web3.solidity_keccak function
        because it was giving incorrect results.
        One important part is to pad all the fields to 32 bytes
        """
        order_type = 1
        packed_data = (
            order_type.to_bytes(1, byteorder='big').rjust(32, b'\0') +  # uint8
            int_to_bytes(self.expire_at) +  # uint256
            int_to_bytes(self.amm_index) +  # uint256
            Web3.to_bytes(hexstr=self.trader).rjust(32, b'\0') +  # address
            int_to_bytes(self.base_asset_quantity) +  # int256
            int_to_bytes(self.price) +  # uint256
            int_to_bytes(self.salt) +  # uint256
            (b'\x01' if self.reduce_only else b'\x00').rjust(32, b'\0')  # bool
        )
        return Web3.keccak(packed_data)


@dataclass
class OrderStatusResponse:
    executedQty: str
    orderId: str
    origQty: str
    price: str
    reduceOnly: bool
    postOnly: bool
    positionSide: str
    status: str
    symbol: int
    time: int
    type: str
    updateTime: int
    salt: int


@dataclass
class OrderBookDepthResponse:
    lastUpdateId: int
    E: int
    T: int
    symbol: int
    bids: List[List[str]]
    asks: List[List[str]]


class Market(int):
    pass


@dataclass
class Position:
    market: Market
    openNotional: str
    size: str
    unrealisedFunding: str
    liquidationThreshold: str
    notionalPosition: str
    unrealisedProfit: str
    marginFraction: str
    liquidationPrice: str
    markPrice: str


@dataclass
class GetPositionsResponse:
    margin: str
    reservedMargin: str
    positions: List[Position]


@dataclass
class Message:
    jsonrpc: str
    id: int
    method: str
    params: List[Any]


@dataclass
class Params:
    subscription: str
    result: Any


@dataclass
class WebsocketResponse:
    jsonrpc: str
    method: str
    params: Params


@dataclass
class OrderBookDepthUpdateResponse:
    T: int
    symbol: int
    bids: List[List[str]]
    asks: List[List[str]]


@dataclass
class OpenOrder:
    Market: int
    Price: str
    Size: str
    FilledSize: str
    Timestamp: int
    Salt: str
    OrderId: str
    ReduceOnly: bool
    PostOnly: bool
    OrderType: str


@dataclass
class Trade:
    BlockNumber: int
    TransactionHash: HexBytes
    Market: int
    Timestamp: int
    TradedAmount: float
    Price: float
    RealizedPnl: float
    OpenNotional: float
    ExecutionMode: str


@dataclass
class TraderFeedUpdate:
    Trader: Address
    OrderId: HexBytes
    OrderType: str
    Removed: bool
    EventName: str
    Args: Dict
    BlockNumber: int
    BlockStatus: str
    Timestamp: int
    TransactionHash: HexBytes


@dataclass
class MarketFeedUpdate:
    Trader: Address
    Market: int
    Size: float
    Price: float
    Removed: bool
    EventName: str
    BlockNumber: int
    BlockStatus: str
    Timestamp: int
    TransactionHash: HexBytes


class TransactionMode(Enum):
    no_wait = 0
    wait_for_head = 1
    wait_for_accept = 2


class ExecutionMode(Enum):
    Taker = 0
    Maker = 1
    SameBlock = 2  # not used
    Liquidation = 3


class OrderStatus(Enum):
    Invalid = 0
    Placed = 1
    Filled = 2
    Cancelled = 3
    PartiallyFilled = 4  # this status is for sdk only; not present in contract


class AsyncOrderBookDepthCallback(Protocol):
    def __call__(self, response: OrderBookDepthResponse) -> Coroutine[Any, Any, Any]: ...


class AsyncPositionCallback(Protocol):
    def __call__(self, response: GetPositionsResponse) -> Coroutine[Any, Any, Any]: ...


class AsyncOrderStatusCallback(Protocol):
    def __call__(self, response: OrderStatusResponse) -> Coroutine[Any, Any, Any]: ...


class AsyncPlaceOrdersCallback(Protocol):
    def __call__(self, response: List[Any]) -> Coroutine[Any, Any, Any]: ...


class AsyncSubscribeToOrderBookDepthCallback(Protocol):
    def __call__(self, ws, response: OrderBookDepthUpdateResponse) -> Coroutine[Any, Any, Any]: ...


class ConfirmationMode(Enum):
    head = "head"
    accepted = "accepted"


def int_to_bytes(value: int):
    return value.to_bytes(32, 'big', signed=True)
