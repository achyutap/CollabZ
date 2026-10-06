from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.explore import service

router = APIRouter()


@router.get("/explore/people")
def explore_people(q: str | None = None, role: str | None = None, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.people(conn, q, role)


@router.get("/explore/projects")
def explore_projects(q: str | None = None, skill: str | None = None, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.projects(conn, q, skill)


@router.get("/explore/projects/{project_id}")
def explore_project(project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.project_detail(conn, project_id, user)
