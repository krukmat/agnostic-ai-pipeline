import pytest
from project.backend-fastapi.app.cart import get_cart, add_to_cart, remove_from_cart

def test_get_cart_empty():
    assert get_cart() == {}

def test_add_to_cart():
    add_to_cart('item1', 2)
    assert get_cart() == {'item1': 2}

def test_remove_from_cart():
    add_to_cart('item1', 2)
    remove_from_cart('item1')
    assert get_cart() == {}