# Python SDK for Hubble Exchange

[Hubble Exchange](https://hubble.exchange) is a decentralized exchange built on Avalanche subnet.


## Installation

The simplest way is to install the package from PyPI:
```shell
pip install hubble-exchange
```

## Example usage:

Requires HUBBLE_RPC_HOST and HUBBLE_BLOCKCHAIN_ID environment variable to be set
```shell
export HUBBLE_RPC_HOST=candy-hubblenet-rpc.hubble.exchange
export HUBBLE_BLOCKCHAIN_ID=iKMFgo49o4X3Pd3UWUkmPwjKom3xZz3Vo6Y1kkwL2Ce6DZaPm
```

```python
import os
from hubble_exchange import HubbleClient, OrderBookDepthResponse


def main():
    client = HubbleClient(os.getenv("PRIVATE_KEY"))
    # place an order for market = 0, amount = 0.2, price = 1800, reduce_only = False
    order = client.place_order(0, 0.2, 1800, False)

    # place multiple orders at once
    orders = []
    orders.append(Order.new(3, 1, 1.2, False)) # market = 3, qty = 1, price = 1.2, reduce_only = False
    orders.append(Order.new(0, 0.1, 1800, False)) # market = 0, qty = 0.1, price = 1800, reduce_only = False
    # placed_orders list will contain the order ids for the orders placed
    placed_orders = client.place_orders(orders)

    # get order status
    order_status = client.get_order_status(order.Id)
    
    # cancel an order
    client.cancel_orders([order])

    # order can also be cancelled by order id
    client.cancel_order_by_id(order.id)

    # get current order book for market = 1
    order_book = client.get_order_book(1)

    # get current margin and positions(uses the address for which private key is set)
    positions = client.get_margin_and_positions()

    # subscribe to order book updates for market = 0; receives a new message every second(only for those prices where the quantity has changed)
    # this is a blocking operation, so it needs to run in a separate thread
    def callback(ws, message: OrderBookDepthResponse):
        print(f"Received orderbook update: {message}")

    client.subscribe_to_order_book_depth(0, callback=callback)


if __name__ == "__main__":
    main()
```
