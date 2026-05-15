from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import LGPD_EXPORT_RATE_LIMIT, limiter
from app.db.session import get_db
from app.modules.audit.service import get_client_ip, get_user_agent, log_action
from app.modules.data_export.schemas import DataExportOut
from app.modules.data_export.service import export_user_data

router = APIRouter(tags=["LGPD"])


@router.get("/me/export", response_model=DataExportOut)
@limiter.limit(LGPD_EXPORT_RATE_LIMIT)
def export_my_data(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        payload = export_user_data(db, user=current_user)
        log_action(
            db,
            user_id=current_user.id,
            action="DATA_EXPORT_REQUEST",
            resource_type="data_export",
            resource_id=current_user.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={"sections": list(payload.keys())},
        )
        return JSONResponse(
            content=jsonable_encoder(payload),
            headers={"Content-Disposition": 'attachment; filename="export.json"'},
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to export data",
        )
