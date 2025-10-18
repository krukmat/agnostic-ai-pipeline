from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from project.backend-fastapi.app.database import get_db
from project.backend-fastapi.app.models.user import User, UserCreate

router = APIRouter()

class UserLogin(BaseModel):
    email: str
    password: str

@router.post('/register', status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail='Email already registered')
    new_user = User(email=user.email, hashed_password=user.hashed_password)
    db.add(new_user)
    db.commit()
    return {'message': 'User registered successfully'}

@router.post('/login', status_code=status.HTTP_200_OK)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    user_db = db.query(User).filter(User.email == user.email).first()
    if not user_db or not user_db.verify_password(user.password):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return {'message': 'Login successful'}