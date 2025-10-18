from fastapi import APIRouter

router = APIRouter()

@router.get("/products")
def get_products():
    return {"products": []}
