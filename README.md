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
    # place an order for market = 0, amount = 0.2, price = 1800, reduce_only = False
    order = await client.place_single_order(0, 0.2, 1800, False, callback)

    # place multiple orders at once
    orders = []
    orders.append(Order.new(3, 1, 1.2, False)) # market = 3, qty = 1, price = 1.2, reduce_only = False
    orders.append(Order.new(0, 0.1, 1800, False)) # market = 0, qty = 0.1, price = 1800, reduce_only = False
    # placed_orders list will contain the order ids for the orders placed
    placed_orders = await client.place_orders(orders, callback)

    # get order status
    order_status = await client.get_order_status(order.Id, callback)
    
    # cancel an order
    await client.cancel_orders([order], callback)

    # order can also be cancelled by order id
    await client.cancel_order_by_id(order.id, callback)

    # get current order book for market = 1
    order_book = await client.get_order_book(1, callback)

    # get current margin and positions(uses the address for which private key is set)
    positions = await client.get_margin_and_positions(callback)

    # get order fills
    order_fills = await client.get_order_fills

    # subscribe to order book updates for market = 0; receives a new message every second(only for those prices where the quantity has changed)
    async def on_message(ws, message):
        print(f"Received orderbook update: {message}")

    asyncio.run(client.subscribe_to_order_book_depth(0, callback=on_message))
```

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
