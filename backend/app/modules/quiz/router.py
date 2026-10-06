from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_role
from app.modules.quiz import service
from app.modules.quiz.schemas import StartBody, SubmitBody

router = APIRouter()


@router.get("/quiz/skills")
def quiz_skills(user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.list_skills(conn, user)


@router.post("/quiz/start")
def quiz_start(body: StartBody, user: CurrentUser = Depends(require_role("student")), conn=Depends(get_db)):
    return service.start(conn, user, body.skills)


@router.post("/quiz/submit")
def quiz_submit(body: SubmitBody, user: CurrentUser = Depends(require_role("student")), conn=Depends(get_db)):
    return service.submit(conn, user, body.attempt_token, [a.model_dump() for a in body.answers])
