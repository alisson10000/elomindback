import os

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.modules.data_deletion_requests.schemas import (
    DataDeletionRequestOut,
    DataDeletionRequestCreateOut,
)
from app.modules.data_deletion_requests.service import (
    create_data_deletion_request,
    get_my_latest_deletion_request,
    execute_full_deletion,  # ✅ NOVO
)

router = APIRouter(tags=["LGPD"])


def require_client(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user


@router.post("/data-deletion-request", response_model=DataDeletionRequestCreateOut)
def request_data_deletion(
    db: Session = Depends(get_db),
    user=Depends(require_client),
):
    """
    Cliente solicita exclusão total (LGPD).
    Regra: não pode existir outra solicitação pendente.
    """
    req = create_data_deletion_request(db, client=user)
    return req


@router.get("/data-deletion-request", response_model=DataDeletionRequestOut | None)
def get_my_data_deletion_request(
    db: Session = Depends(get_db),
    user=Depends(require_client),
):
    """
    Retorna a última solicitação do cliente (se houver).
    """
    return get_my_latest_deletion_request(db, client_id=user.id)


# ✅ ADMIN (MVP): executa exclusão manual (sem mexer no fluxo do cliente)
@router.post("/admin/data-deletion-execute/{client_id}")
def admin_execute_data_deletion(
    client_id: int,
    db: Session = Depends(get_db),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    """
    Executa a exclusão total dos dados do cliente (MVP manual).
    Protegido por X-Admin-Key.
    """

    expected = os.getenv("ADMIN_KEY", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_KEY not configured",
        )

    if x_admin_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )

    execute_full_deletion(db=db, client_id=client_id)
    return {"status": "ok", "client_id": client_id}
