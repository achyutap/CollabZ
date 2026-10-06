import sqlite3
from typing import List

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user

from . import service
from .schemas import CountsOut, NotificationOut, OkOut

router = APIRouter()


@router.get("/notifications", response_model=List[NotificationOut])
def list_notifications(unread_only: bool = False, user: CurrentUser = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    return service.list_notifications(conn, user.id, unread_only)


@router.post("/notifications/read-all", response_model=OkOut)
def read_all(user: CurrentUser = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    return service.mark_all_read(conn, user.id)


@router.post("/notifications/{notification_id}/read", response_model=OkOut)
def read_one(notification_id: str, user: CurrentUser = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    return service.mark_read(conn, user.id, notification_id)


@router.get("/me/counts", response_model=CountsOut)
def my_counts(user: CurrentUser = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    return service.counts(conn, user.id, user.role)
