import sqlite3

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user

from . import service
from .schemas import AuthOut, LoginIn, RegisterIn, ResearcherOut, StudentOut, UserOut, WalletOut

router = APIRouter()


@router.post("/auth/register", response_model=AuthOut)
def register(body: RegisterIn, conn: sqlite3.Connection = Depends(get_db)):
    return service.register(conn, body)


@router.post("/auth/login", response_model=AuthOut)
def login(body: LoginIn, conn: sqlite3.Connection = Depends(get_db)):
    return service.login(conn, body.email, body.password)


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    return service.me(conn, user.id)


@router.get("/researchers/{researcher_id}", response_model=ResearcherOut)
def researcher(researcher_id: str, user: CurrentUser = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    return service.get_researcher(conn, researcher_id)


@router.get("/students/{student_id}", response_model=StudentOut)
def student(student_id: str, user: CurrentUser = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    return service.get_student(conn, student_id, user.id)


@router.get("/me/wallet", response_model=WalletOut)
def my_wallet(user: CurrentUser = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    return service.wallet(conn, user.id)
