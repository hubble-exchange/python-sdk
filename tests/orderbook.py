import os

import pytest

from hubble_exchange import HubbleClient, Order, TransactionMode
from hubble_exchange.errors import OrderNotFound

client = HubbleClient(os.getenv("PRIVATE_KEY"))

def test_get_order_book():
    order_book = client.get_order_book(0)
    print(order_book)


def test_get_margin_and_positions():
    positions = client.get_margin_and_positions()
    print(positions)


def test_place_single_order():
    order = client.place_single_order(0, 0.01, 1800, False, mode=TransactionMode.wait_for_accept)
    print(order)

    status = client.get_order_status(order.id)
    assert status.origQty == '0.01000000'
    assert status.price == '1800.00000000'
    assert status.reduceOnly == False
    assert status.symbol == 0


def test_place_orders():
    orders = place_orders()
    print(orders)

    status = client.get_order_status(orders[0].id)
    assert status.origQty == '0.01000000'
    assert status.positionSide == 'LONG'
    assert status.price == '1800.00000000'
    assert status.reduceOnly == False
    assert status.symbol == 0

    status = client.get_order_status(orders[1].id)
    assert status.origQty == '0.01000000'
    assert status.positionSide == 'SHORT'
    assert status.price == '1801.00000000'
    assert status.reduceOnly == False
    assert status.symbol == 0


def test_cancel_orders():
    orders = place_orders()
    print(orders)

    client.cancel_orders(orders, mode=TransactionMode.wait_for_accept)

    with pytest.raises(OrderNotFound):
        client.get_order_status(orders[0].id)

    with pytest.raises(OrderNotFound):
        client.get_order_status(orders[1].id)


def test_cancel_order_by_id():
    order = client.place_single_order(0, 0.01, 1800, False, mode=TransactionMode.wait_for_accept)
    print(order)

    client.cancel_order_by_id(order.id, mode=TransactionMode.wait_for_accept)

    with pytest.raises(OrderNotFound):
        client.get_order_status(order.id)


def place_orders():
    orders = []
    orders.append(Order.new(0, 0.01, 1800, False))
    orders.append(Order.new(0, -0.01, 1801, False))
    return client.place_orders(orders, mode=TransactionMode.wait_for_accept)
