import asyncio
from datetime import datetime
import glob
import os
import time
from hexbytes import HexBytes

import requests
# from hubble_exchange import HubbleClient
from hubble_exchange import HubbleClient, OrderBookDepthResponse, LimitOrder, TransactionMode
from hubble_exchange.eth import get_rpc_endpoint
from hubble_exchange.indexer_client import IndexerClient
from hubble_exchange.models import ConfirmationMode, IOCOrder

# set a global var
start = datetime.utcnow().timestamp()


async def callback(response=None, arg2=None) -> None:
    # print('received', response, arg2)
    return response


async def main():
    """
    """
    global start
    start = datetime.utcnow().timestamp()
    # print('before everything = ', datetime.utcnow().timestamp())
    client = HubbleClient(os.getenv("PRIVATE_KEY")) # type: ignore
    # client.set_transaction_mode(TransactionMode.wait_for_accept)

    # await client.get_balance(callback)
    # indexer_client = IndexerClient()
    # response = indexer_client.get_predicted_funding_rate("arb-perp")
    # response = await client.get_predicted_funding_rate(2)
    # response = await client.get_candlesticks(0, "5m", 1696910799, 1696920799)
    # response = indexer_client.get_historical_funding_rate("arb-perp", 1696920799)
    # response = await client.get_funding_rate(2, 1696920799)
    # response = indexer_client.get_historical_open_interest("arb-perp", 1696920799)
    # response = await client.get_open_interest(2, 1696920799)
    # print(response)
    # res = await client.get_markets()
    # print(res)
    # return

    # await client.subscribe_to_trader_updates(ConfirmationMode.accepted, callback)
    # orders = []
    # for i in range(3):
    #     orders.append(Order.new(7, -1, 0.09, False))
        # orders.append(Order.new(0, 1, 0.1, False))
    # await client.place_orders(orders, callback)

    # await client.get_open_orders(None, callback)

    # order = LimitOrder.new(7, -1, 0.0636, False, False)
    # order = LimitOrder.new(2, 40, 0.818, False, False)
    # print('before placing order time = ', start)
    # order_id = response[0]['order_id']
    # for i in range(5):
    #     # order = LimitOrder.new(0, 0.01, 2000, False, False)
    #     order = IOCOrder.new(0, 0.01, 2000, False, 5)
    #     start = datetime.utcnow().timestamp()
    #     # print('before placing order time = ', start)
    #     response = await client.place_ioc_orders([order], False, callback)
    #     print('time taken = ', datetime.utcnow().timestamp() - start)
        # time.sleep(1)

    # print("response = ", response)
    # await client.cancel_order_by_id(response[0]['order_id'], True, callback)
    # await client.get_limit_order_status(response[0]['order_id'], callback)
    # await client.get_limit_order_details(response[0]['order_id'], callback)
    # await client.get_open_orders(None, callback)
    # await client.cancel_limit_orders([order], True, callback)
    # return
    # nonce = await client.get_nonce()
    # print(nonce)

    # await client.get_limit_order_status("0x24d1166c068cc5982a7ec5c45a80e34e2b5c83c205f39dc77f325a9db72cb9ea", callback)
    # await client.get_limit_order_status("0x96fceb653f71ffa2628b06ce33a8069f5764caf45146200a4ed221e95fa16ac0", callback)

    # orders = [IOCOrder.new(2, 40, 0.7, False, 3)]
    # response = await client.place_ioc_orders(orders, True, callback)
    # print(response)
    # # return

    # end = int(time.time())
    # await client.get_trades(0, end - 10000, end, callback)
    # await client.get_trades(None, end - 86400, end, callback)

    for i in range(10):
        start = datetime.utcnow().timestamp()
        orders = [LimitOrder.new(0, 1, 1800, False, False)]
        response = await client.place_limit_orders(orders, True, callback)
        print('time taken = ', datetime.utcnow().timestamp() - start)
        # print(response)
    await client.close_websocket()

    # res = await client.get_markets()
    # print(res)
    # orders = await client.place_orders([Order.new(7, 1, 0.1, False)], callback)

    # task1 = asyncio.create_task(client.get_order_status(orders[0].id, callback))
    # task2 = asyncio.create_task(client.get_order_status(orders[0].id, callback))
    # task3 = asyncio.create_task(client.get_order_status(orders[0].id, callback))
    # task4 = asyncio.create_task(client.get_order_status(orders[0].id, callback))
    # task5 = asyncio.create_task(client.get_order_status(orders[0].id, callback))

    # task1 = asyncio.create_task(client.place_orders([Order.new(7, 1, 0.1, False)], callback))
    # task2 = asyncio.create_task(client.place_orders([Order.new(7, 1, 0.1, False)], callback))
    # task3 = asyncio.create_task(client.place_orders([Order.new(7, 1, 0.1, False)], callback))
    # task4 = asyncio.create_task(client.place_orders([Order.new(7, 1, 0.1, False)], callback))
    # task5 = asyncio.create_task(client.place_orders([Order.new(7, 1, 0.1, False)], callback))

    # await task1
    # await task2
    # await task3
    # await task4
    # await task5

    # cancel_orders()
    # r = await client.get_margin_and_positions(callback)
    # r = await client.web3_client.eth.get_margin_and_positions("0x3ABDCd346dB73bEB3e9BBE2cB336c91eec507a28")
    # print(r)

    # await client.subscribe_to_order_book_depth(2, callback)    
    # await client.subscribe_to_trader_updates(ConfirmationMode.head, callback)
    # await client.subscribe_to_market_updates(2, ConfirmationMode.head, callback)

async def cancel_orders():
    client = HubbleClient(os.getenv("PRIVATE_KEY"))
    client.set_transaction_mode(TransactionMode.wait_for_head)
    request_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "orderbook_getOpenOrders",
        "params": [client.trader_address, "7"],
    }
    response = requests.post(get_rpc_endpoint(), json=request_body)
    response_json = response.json()

    # print(response_json)
    print(len(response_json["result"]["Orders"]))
    # print(response_json["result"]["Orders"][0])
    # return
    i = 0
    orders = []
    for order in response_json["result"]["Orders"]:
        # print(order["OrderId"])
        ord = LimitOrder(
            id=None,
            amm_index=order["Market"],
            base_asset_quantity=int(order["Size"]),
            price=int(order["Price"]),
            reduce_only=order["ReduceOnly"],
            salt=int(order["Salt"]),
            trader=client.trader_address
        )
        orders.append(ord)
        # client.cancel_order_by_id(HexBytes(order["OrderId"]))

    # chunkify order
    await client.cancel_limit_orders(orders[i:i+5], True, callback)
    return

    for i in range(0, len(orders), 100):
        await client.cancel_orders(orders[i:i+100], True, callback)
        time.sleep(0.2)
        print(i)
        # return
    # client.cancel_orders([ord])
    # time.sleep(0.2)
    # i = i+ 1
    # if i % 50 == 0:
        # print(i)
if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.run(cancel_orders())
    # cancel_orders()
