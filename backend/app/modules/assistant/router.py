from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.assistant import service
from app.modules.assistant.schemas import ChatBody

router = APIRouter()


@router.post("/projects/{project_id}/chat")
def post_chat(project_id: str, body: ChatBody, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.send(conn, project_id, user, body.message)


@router.get("/projects/{project_id}/chat")
def get_chat(project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.history(conn, project_id, user)
