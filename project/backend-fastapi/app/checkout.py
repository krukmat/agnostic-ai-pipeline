from fastapi import APIRouter

router = APIRouter()

@router.get("/checkout")
def checkout():
    return {"status": "success", "message": "Checkout successful"}
