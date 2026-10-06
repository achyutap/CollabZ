from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.projects import service as svc
from app.modules.projects.schemas import ShareIn, SkillNeedIn

router = APIRouter()


@router.get("/projects")
def list_projects(user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.list_projects(conn, user)


@router.get("/projects/{project_id}")
def get_project(project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.get_detail(conn, user, project_id)


@router.post("/projects/{project_id}/skill-needs")
def set_skill_needs(project_id: str, body: list[SkillNeedIn], user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.set_skill_needs(conn, user, project_id, body)


@router.delete("/projects/{project_id}/members/{student_id}")
def remove_member(project_id: str, student_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.remove_member(conn, user, project_id, student_id)


@router.put("/projects/{project_id}/researcher-shares")
def put_shares(project_id: str, body: list[ShareIn], user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.set_shares(conn, user, project_id, body)


@router.get("/projects/{project_id}/counts")
def get_counts(project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.counts(conn, user, project_id)
