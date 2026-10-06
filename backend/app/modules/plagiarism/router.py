from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user

from . import service
from .schemas import MyIntegrityItem, ProjectIntegrityItem

router = APIRouter()


@router.get("/projects/{project_id}/integrity", response_model=list[ProjectIntegrityItem])
def project_integrity(
    project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)
):
    return service.project_integrity(conn, user, project_id)


@router.get("/me/integrity", response_model=list[MyIntegrityItem])
def my_integrity(user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.my_integrity(conn, user)
