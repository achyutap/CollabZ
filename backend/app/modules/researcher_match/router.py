from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.modules.researcher_match import service as svc
from app.modules.researcher_match.schemas import RequestsCreate, RespondBody

router = APIRouter()


@router.get("/problems/{problem_id}/matches")
def get_matches(problem_id: str, user: CurrentUser = Depends(require_role("sponsor")), conn=Depends(get_db)):
    return svc.matches(conn, user, problem_id)


@router.post("/problems/{problem_id}/requests")
def create_requests(problem_id: str, body: RequestsCreate, user: CurrentUser = Depends(require_role("sponsor")), conn=Depends(get_db)):
    return svc.create_requests(conn, user, problem_id, body.researcher_ids)


@router.get("/problems/{problem_id}/requests")
def list_problem_requests(problem_id: str, user: CurrentUser = Depends(require_role("sponsor")), conn=Depends(get_db)):
    return svc.problem_requests(conn, user, problem_id)


@router.get("/researcher/requests")
def list_my_requests(user: CurrentUser = Depends(require_role("researcher")), conn=Depends(get_db)):
    return svc.my_requests(conn, user)


@router.post("/researcher-requests/{request_id}/respond")
def respond(request_id: str, body: RespondBody, user: CurrentUser = Depends(require_role("researcher")), conn=Depends(get_db)):
    return svc.respond(conn, user, request_id, body.accept)
