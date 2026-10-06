from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user

from . import service
from .schemas import PayoutOut

router = APIRouter()


@router.post("/projects/{project_id}/complete", response_model=PayoutOut)
def complete_project(
    project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)
):
    return service.complete_project(conn, user, project_id)


@router.get("/projects/{project_id}/payout", response_model=PayoutOut)
def get_payout(project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.get_payout(conn, user, project_id)
