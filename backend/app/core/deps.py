import sqlite3
from dataclasses import dataclass

from fastapi import Depends, Request

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import decode_token


@dataclass
class CurrentUser:
    id: str
    role: str
    name: str
    email: str


def get_current_user(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> CurrentUser:
    header = request.headers.get("Authorization", "")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AppError(401, "UNAUTHORIZED", "Missing or invalid Authorization header")
    claims = decode_token(parts[1])
    row = conn.execute("SELECT id, role, name, email, is_blacklisted FROM users WHERE id=?", (claims["sub"],)).fetchone()
    if row is None:
        raise AppError(401, "UNAUTHORIZED", "User not found")
    if row["is_blacklisted"]:
        raise AppError(403, "BLACKLISTED", "Your account has been blocked due to repeated plagiarism.")
    return CurrentUser(id=row["id"], role=row["role"], name=row["name"], email=row["email"])


def require_role(*roles: str):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise AppError(403, "FORBIDDEN", "Requires role: " + ", ".join(roles))
        return user

    return dependency
