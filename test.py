import warnings
warnings.filterwarnings("ignore")

import time
import os
from hubble_exchange import HubbleClient, OrderBookDepthResponse

def main():
    """
    """
    client = HubbleClient(os.getenv("PRIVATE_KEY"))

    # order_book = client.get_order_book(1)
    # print(order_book)

    # positions = client.get_margin_and_positions()
    # print(positions)

    order = client.place_order(0, 0.2, 1800, False)
    print(order)
    # order = client.place_order(0, 0.2, 1801, False)
    # print(order)
    # order = client.place_order(0, 0.2, 1802, False)
    # print(order)
    # order = client.place_order(0, -0.2, 1803, False)
    # print(order)

    # order_status = client.get_order_status(order.id)
    # print(order_status)

    def on_message(ws, message: OrderBookDepthResponse):
        print(f"Received message: {message}")

    client.subscribe_to_order_book_depth(0, callback=on_message)
    # ws_app.on_data = lambda data: print('data', data)
    # ws_app.on_message = lambda msg: print('msg', msg)

    time.sleep(5)
    client.cancel_orders([order])
    # client.cancel_order_by_id(order.Id)
    

if __name__ == "__main__":
    main()
