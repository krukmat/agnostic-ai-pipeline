from app.order import get_product
import pytest
def test_get_product():
    assert get_product(1) == {'id': 1, 'name': 'Product 1'}