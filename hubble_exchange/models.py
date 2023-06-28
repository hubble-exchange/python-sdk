from dataclasses import dataclass
from typing import List
from eth_typing import Address
from hexbytes import HexBytes


@dataclass
class Order:
    id: HexBytes
    amm_index: int
    trader: Address
    base_asset_quantity: int
    price: int
    salt: int
    reduce_only: bool

    def to_dict(self):
        return {
            "ammIndex": self.amm_index,
            "trader": self.trader,
            "baseAssetQuantity": self.base_asset_quantity,
            "price": self.price,
            "salt": self.salt,
            "reduceOnly": self.reduce_only,
        }


@dataclass
class OrderStatusResponse:
    executedQty: str
    orderId: str
    origQty: str
    price: str
    reduceOnly: bool
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
    symbol: int
    E: int
    T: int
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
    params: List[any]


@dataclass
class Params:
    subscription: str
    result: any


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
