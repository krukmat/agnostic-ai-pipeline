from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from project.backend-fastapi.app.database import get_db

router = APIRouter()

class ShippingDetails(BaseModel):
    address: str
    city: str
    state: str
    zip_code: str
    country: str

@router.post('/order', response_model=dict)
def create_order(shipping_details: ShippingDetails, db: Session = Depends(get_db)):
    return {'status': 'Order created successfully'}