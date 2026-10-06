from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.profiles import service
from app.modules.profiles.schemas import ProfilePatch

router = APIRouter()


@router.get("/me/profile")
def my_profile(user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.get_profile(conn, user.id, user)


@router.patch("/me/profile")
def patch_my_profile(body: ProfilePatch, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.update_profile(conn, user, body)


@router.get("/users/{user_id}/profile")
def user_profile(user_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.get_profile(conn, user_id, user)


@router.post("/users/{user_id}/like")
def like_user(user_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.like(conn, user_id, user)


@router.delete("/users/{user_id}/like")
def unlike_user(user_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.unlike(conn, user_id, user)
