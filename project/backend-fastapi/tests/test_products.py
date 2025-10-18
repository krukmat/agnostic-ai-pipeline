import pytest
from app.products import get_product, list_products

def test_get_product():
    product = get_product(1)
    assert product['id'] == 1

def test_list_products():
    products = list_products()
    assert len(products) > 0