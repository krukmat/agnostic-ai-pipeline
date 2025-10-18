from fastapi import APIRouter

cart_router = APIRouter()

@cart_router.get('/cart', status_code=200)
def get_cart():
    return {'status': 'ok', 'message': 'Cart details'}

@cart_router.post('/cart/add', status_code=201)
def add_to_cart(item_id: int):
    return {'status': 'ok', 'message': f'Item {item_id} added to cart'}

@cart_router.delete('/cart/remove/{item_id}', status_code=204)
def remove_from_cart(item_id: int):
    return {'status': 'ok', 'message': f'Item {item_id} removed from cart'}