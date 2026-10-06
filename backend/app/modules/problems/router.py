from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_role
from app.modules.problems import service as svc
from app.modules.problems.schemas import ProblemCreate, SkillsPatch

router = APIRouter()


@router.post("/problems")
def create_problem(body: ProblemCreate, user: CurrentUser = Depends(require_role("sponsor")), conn=Depends(get_db)):
    return svc.create_problem(conn, user, body)


@router.get("/problems")
def list_problems(user: CurrentUser = Depends(require_role("sponsor", "researcher")), conn=Depends(get_db)):
    return svc.list_problems(conn, user)


@router.get("/problems/{problem_id}")
def get_problem(problem_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return svc.get_problem(conn, user, problem_id)


@router.patch("/problems/{problem_id}/skills")
def patch_skills(problem_id: str, body: SkillsPatch, user: CurrentUser = Depends(require_role("sponsor")), conn=Depends(get_db)):
    return svc.patch_skills(conn, user, problem_id, body.required_skills)
