from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.modules.auth.schemas import SignupIn, LoginIn, TokenOut, MeOut
from app.modules.auth.service import signup, login
from app.modules.users.service import serialize_user

router = APIRouter()

@router.post("/signup", response_model=TokenOut)
def signup_route(payload: SignupIn, db: Session = Depends(get_db)):
    token = signup(
        db,
        email=payload.email,
        name=payload.name,
        role=payload.role,
        password=payload.password,
    )
    return {"access_token": token}

@router.post("/login", response_model=TokenOut)
def login_route(payload: LoginIn, db: Session = Depends(get_db)):
    token = login(db, email=payload.email, password=payload.password)
    return {"access_token": token}

@router.get("/me", response_model=MeOut)
def me_route(user=Depends(get_current_user)):
    return serialize_user(user)
