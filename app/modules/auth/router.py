from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.schemas import SignupIn, LoginIn, TokenOut
from app.modules.auth.service import signup, login

router = APIRouter()

@router.post("/signup", response_model=TokenOut)
def signup_route(payload: SignupIn, db: Session = Depends(get_db)):
    token = signup(db, email=payload.email, name=payload.name, role=payload.role, password=payload.password)
    return {"access_token": token}

@router.post("/login", response_model=TokenOut)
def login_route(payload: LoginIn, db: Session = Depends(get_db)):
    token = login(db, email=payload.email, password=payload.password)
    return {"access_token": token}
