from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.modules.reflections.schemas import ReflectionCreate, ReflectionOut
from app.modules.reflections.service import create_reflection, list_my_reflections

router = APIRouter()

@router.post("/", response_model=ReflectionOut)
def create(payload: ReflectionCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # MVP: só cliente cria reflexão
    ref = create_reflection(db, client_id=user.id, data=payload)
    return ref

@router.get("/me", response_model=list[ReflectionOut])
def my_history(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return list_my_reflections(db, client_id=user.id)
