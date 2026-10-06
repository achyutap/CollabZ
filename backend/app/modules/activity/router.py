from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.activity import service
from app.modules.activity.schemas import ActivityItem

router = APIRouter()


@router.get("/projects/{project_id}/activity", response_model=list[ActivityItem])
def project_activity(
    project_id: str,
    user_id: str | None = None,
    limit: int = 100,
    user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_db),
):
    return service.list_activity(conn, project_id, user, user_id, limit)
