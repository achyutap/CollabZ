from typing import Optional

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_role
from app.modules.student_match import service as svc
from app.modules.student_match.schemas import RespondBody, StudentRequestCreate

router = APIRouter()


@router.get("/projects/{project_id}/shortlist")
def get_shortlist(project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.shortlist(conn, user, project_id)


@router.get("/projects/{project_id}/student-search")
def student_search(project_id: str, q: Optional[str] = None, skill: Optional[str] = None, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.search(conn, user, project_id, q, skill)


@router.post("/projects/{project_id}/student-requests")
def create_request(project_id: str, body: StudentRequestCreate, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.create_request(conn, user, project_id, body.student_id, body.skill)


@router.get("/projects/{project_id}/student-requests")
def list_project_requests(project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.project_requests(conn, user, project_id)


@router.get("/student/requests")
def list_my_requests(user: CurrentUser = Depends(require_role("student")), conn=Depends(get_db)):
    return svc.my_requests(conn, user)


@router.post("/student-requests/{request_id}/respond")
def respond(request_id: str, body: RespondBody, user: CurrentUser = Depends(require_role("student")), conn=Depends(get_db)):
    return svc.respond(conn, user, request_id, body.accept)
