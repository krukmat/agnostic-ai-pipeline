from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from project.backend-fastapi.app.database import get_db
from project.backend-fastapi.app.models.user import User, UserCreate
from project.backend-fastapi.app.auth import router as auth_router

app = FastAPI()

app.include_router(auth_router)

class HealthCheck(BaseModel):
    status: str

@app.get('/health', response_model=HealthCheck)
def health_check():
    return {'status': 'ok'}