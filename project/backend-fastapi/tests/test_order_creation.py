import pytest
from app.order import create_order

def test_create_order():
    order_data = {
        'customer_id': 1,
        'items': [{'product_id': 1, 'quantity': 2}, {'product_id': 2, 'quantity': 1}]
    }
    result = create_order(order_data)
    assert result['status'] == 'success'
