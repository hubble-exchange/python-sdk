# Python SDK for Hubble Exchange

[Hubble Exchange](https://hubble.exchange) is a Layer 1 Blockchain for a Decentralised Perps OrderBook
<br>[Twitter](https://twitter.com/HubbleExchange)


## Installation

The simplest way is to install the package from PyPI:
```shell
pip install hubble-exchange
```

## Example usage:

All read/write functions are async
<br>Requires HUBBLE_RPC_HOST and HUBBLE_BLOCKCHAIN_ID environment variable to be set
```shell
export HUBBLE_RPC_HOST=candy-hubblenet-rpc.hubble.exchange
export HUBBLE_BLOCKCHAIN_ID=iKMFgo49o4X3Pd3UWUkmPwjKom3xZz3Vo6Y1kkwL2Ce6DZaPm
```

```python
import os
from hubble_exchange import HubbleClient, OrderBookDepthResponse


async def main():

    async def callback(response):
        print(f"Received response: {response}")
        return response

    client = HubbleClient(os.getenv("PRIVATE_KEY"))

    # get a dict of all market ids and names - for example {0: "ETH-Perp", 1: "AVAX-Perp"}
    markets = await client.get_markets()

    # place multiple orders at once
    orders = []
    orders.append(Order.new(3, 1, 1.2, False)) # market = 3, qty = 1, price = 1.2, reduce_only = False
    orders.append(Order.new(0, 0.1, 1800, False)) # market = 0, qty = 0.1, price = 1800, reduce_only = False
    # placed_orders list will contain the order ids for the orders placed
    placed_orders = await client.place_orders(orders, True, callback)

    # get order status
    order_status = await client.get_order_status(order.id, callback)
    
    # cancel an order
    await client.cancel_orders([order], True, True, callback)

    # order can also be cancelled by order id
    await client.cancel_order_by_id(order.id, True, callback)

    # get current order book for market = 1
    order_book = await client.get_order_book(1, callback)

    # get current margin and positions(uses the address for which private key is set)
    positions = await client.get_margin_and_positions(callback)

    # get order fills
    order_fills = await client.get_order_fills()

    # subscribe to order book updates for market = 0; receives a new message every second(only for those prices where the quantity has changed)
    async def on_message(ws, message):
        print(f"Received orderbook update: {message}")

    asyncio.run(client.subscribe_to_order_book_depth(0, callback=on_message))
```

---

### GetPositionsResponse description
- margin: trader's margin
- reservedMargin: trader's reserved margin
- positions: List[Position]

### Position description
- market: market id
- openNotional: open notional
- size: size of the position
- unrealisedFunding: unrealised funding payment for this position
- liquidationThreshold: max amount of size that can be liquidated at once
- notionalPosition: notional position size
- unrealisedProfit: unrealised profit on this position
- marginFraction: margin/notional position
- liquidationPrice: the asset price at which this position might get liquidated
- markPrice: latest price of this market

### OrderStatusResponse description
- executedQty: executed quantity
- orderId: order id
- origQty: total order quantity
- price: order price
- reduceOnly: whether the order is reduce-only or not
- positionSide: (LONG|SHORT)
- status: order status (NEW|FILLED|CANCELED|REJECTED|PARTIALLY_FILLED)
- symbol: market id
- time: time when the order was placed in unix format
- type: LIMIT_ORDER
- updateTime: time when the order was last updated in unix format
- salt: order salt

## Orderbook depth feed
Orderbook depth feed can be subscribed to using the `subscribe_to_order_book_depth` method. It emits the change in orderbook depth every second. It only emits the prices where the quantity has changed, but with absolute quantities(not the change).

```python
import os
from hubble_exchange import HubbleClient

async def main():
    client = HubbleClient(os.getenv("PRIVATE_KEY"))
    # subscribe to market id 0
    await client.subscribe_to_order_book_depth(0, callback=callback)
```

### OrderBookDepthUpdateResponse description
- T: timestamp
- symbol: market id
- bids: list of [price, quantity] for bids
- asks: list of [price, quantity] for asks


## Trader feed

All order updates related to a particular trader can be subscribed to using the `subscribe_to_trader_updates` method.
It can be subscribed in 2 confirmation modes - head block or accepted block. Events received in head block mode are not finalised and can be reverted. When an event is removed from the chain, the client will receive a `removed=True` event. Events received in accepted block mode are finalised and will alwats have `removed=False`.

```python
import os
from hubble_exchange import HubbleClient, ConfirmationMode

async def main():
    client = HubbleClient(os.getenv("PRIVATE_KEY"))
    await client.subscribe_to_trader_updates(ConfirmationMode.accepted, callback)
```


### TraderFeedUpdate description

- Trader: address of the trader
- OrderId: order id
- OrderType: order type - "limit" order or "ioc" (market order)
- Removed: whether the event is being removed or not
- EventName: name of the contract event (OrderPlaced|OrderMatched|OrderCancelled)
- Args: args is a dynamic field and it contains information about the event. OrderPlaced event contains order object, OrderMatched event contains fillAmount and price
- BlockNumber: block number in which the transaction was included
- BlockStatus: (head|accepted) whether the block is accepted or only a preferred block(head block)
- Timestamp: timestamp of the block in unix format
- TransactionHash: transaction hash

Removed events are emmitted during chain reorgs, and are most likely to be temporary. They are only emmitted when subscribing to head block events. If removed=True, the client might need to do a reverse operation for the given event. For example if an OrderMatched event is received with removed=True, the client should add the fillAmount back to unfilled quantity of the order.

## Market feed

All trades of a particular market can be subscribed to using the `subscribe_to_market_updates` method.
Similar to the trader feed, it has 2 confirmation modes - head block or accepted block.

```python
import os
from hubble_exchange import HubbleClient, ConfirmationMode

async def main():
    client = HubbleClient(os.getenv("PRIVATE_KEY"))
    # subscribe to market id 0
    await client.subscribe_to_market_updates(0, ConfirmationMode.accepted, callback)
```

### MarketFeedUpdate description

- Trader: address of the trader who performed the trade
- Market: market id
- Size: size of the trade in decimals
- Price: price at which it was executed
- Removed: whether the event is being removed or not
- EventName: name of the contract event (PositionModified)
- BlockNumber: block number in which the transaction was included
- BlockStatus: (head|accepted) whether the block is accepted or only a preferred block(head block)
- Timestamp: timestamp of the block in unix format
- TransactionHash: transaction hash

Removed events are emmitted during chain reorgs, and are most likely to be temporary. They are only emmitted when subscribing to head block events. If removed=True, the client might need to do a reverse operation for the given event.

---

## Custom transaction options

The following options can be passed to the client to override the default

```python
{
    "nonce": Nonce,
    "gas": int,
    "maxFeePerGas": Union[str, Wei],
    "maxPriorityFeePerGas": Union[str, Wei],
},
```

It can be used for `place_orders`, `place_single_order`, `cancel_orders`, `cancel_order_by_id` methods.
Example:
```python

from web3 import Web3

client = HubbleClient(os.getenv("PRIVATE_KEY"))
placed_orders = await client.place_orders(orders, callback, {
    "gas": 500_000,
    "maxFeePerGas": Web3.to_wei(80, 'gwei'),
    "maxPriorityFeePerGas": Web3.to_wei(20, 'gwei'),
})
```

## Transaction modes

There are different modes in which the client can wait for acknowledgement of the transaction. The default behaviour is to send the transaction and not wait for the acknowledgement.
This can be changed by explicitly asking the function to wait while sending the trasaction.

- TransactionMode.no_wait: The default behaviour is to send transactions to the blockchain and NOT wait for the acknowledgement.
- TransactionMode.wait_for_head: Wait for the transaction to be included in the canonical chain. At this time the block is preferred but not yet finalized. However, once the block in included in the canonical chain, the matching engine will start processing the order.
- TransactionMode.wait_for_accept: Wait for the transaction to be finalised.

Example:
```python
from hubble_exchange import TransactionMode
client = HubbleClient(os.getenv("PRIVATE_KEY"))
placed_orders = await client.place_orders(orders, callback, mode=TransactionMode.wait_for_accept)

# or set the default mode for all transactions

client.set_transaction_mode(TransactionMode.wait_for_head)
```

---

## Waiting for response in place_orders and cancel_orders

The `place_orders` and `cancel_orders` methods can be called in 2 modes - wait for response or don't wait for response.
To get the acknowledgement of the transaction, use `wait_for_response=True`. The response will be a list of dicts with order ids and success boolean. Waiting for response will be slower because this can be confirmed only after the transaction is mined(accepted).
When using `wait_for_response=True`, the sdk will automatically set the transaction mode to `TransactionMode.wait_for_accept` because the response can be confirmed only after the transaction is mined.

Alternatively, the client can also use trader feed to listen to all the updates. This is faster when done with ConfirmationMode.head

## Atomic in cancel_orders

The `cancel_orders` method can be called in 2 modes - atomic or non-atomic. In atomic mode, all the orders will be cancelled only if all the orders are successfully cancelled. In non-atomic mode, the orders will be cancelled one by one and the response will be a list of dicts with order ids and success boolean.
When used in combination with `wait_for_response=True`, the response will be a list of dicts with order ids and success boolean.
