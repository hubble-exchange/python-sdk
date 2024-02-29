import os

import pytest

from hubble_exchange import HubbleClient, Order, TransactionMode
from hubble_exchange.errors import OrderNotFound

client = HubbleClient(os.getenv("PRIVATE_KEY"))

async def callback(response=None):
    return response

@pytest.mark.asyncio
async def test_get_order_book():
    order_book = await client.get_order_book(0, callback)
    assert order_book.symbol == 0


@pytest.mark.asyncio
async def test_get_margin_and_positions():
    positions = await client.get_margin_and_positions(callback)
    assert positions.margin
    assert positions.positions


@pytest.mark.asyncio
async def test_place_single_order():
    order = await client.place_single_order(0, 0.01, 1800, False, callback, mode=TransactionMode.wait_for_accept)

    status = await client.get_order_status(order.id, callback)
    assert status.origQty == '0.01000000'
    assert status.positionSide == 'LONG'
    assert status.price == '1800.00000000'
    assert status.reduceOnly == False
    assert status.symbol == 0


@pytest.mark.asyncio
async def test_place_orders():
    orders = await place_orders()

    status = await client.get_order_status(orders[0].id, callback)
    assert status.origQty == '1.00000000'
    assert status.positionSide == 'LONG'
    assert status.price == '0.10000000'
    assert status.reduceOnly == False
    assert status.symbol == 7

    status = await client.get_order_status(orders[1].id, callback)
    assert status.origQty == '1.00000000'
    assert status.positionSide == 'SHORT'
    assert status.price == '0.12000000'
    assert status.reduceOnly == False
    assert status.symbol == 7


@pytest.mark.asyncio
async def test_cancel_orders():
    orders = await place_orders()

    await client.cancel_orders(orders, callback, mode=TransactionMode.wait_for_accept)

    with pytest.raises(OrderNotFound):
        await client.get_order_status(orders[0].id, callback)

    with pytest.raises(OrderNotFound):
        await client.get_order_status(orders[1].id, callback)


@pytest.mark.asyncio
async def test_cancel_order_by_id():
    order = await client.place_single_order(0, 0.01, 1800, False, callback, mode=TransactionMode.wait_for_accept)

    await client.cancel_order_by_id(order.id, callback, mode=TransactionMode.wait_for_accept)

    with pytest.raises(OrderNotFound):
        await client.get_order_status(order.id, callback)


async def place_orders():
    orders = []
    orders.append(Order.new(7, 1, 0.1, False))
    orders.append(Order.new(7, -1, 0.12, False))
    return await client.place_orders(orders, callback, mode=TransactionMode.wait_for_accept)
