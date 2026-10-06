from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AppError

ALGO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except Exception:
        return False


def sign_payload(payload: dict, minutes: int) -> str:
    data = dict(payload)
    data["exp"] = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode(data, settings.jwt_secret, algorithm=ALGO)


def verify_payload(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise AppError(400, "INVALID_TOKEN", "Invalid or expired token")


def create_access_token(user_id: str, role: str) -> str:
    return sign_payload({"sub": user_id, "role": role}, settings.jwt_expire_minutes)


def decode_token(token: str) -> dict:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise AppError(401, "UNAUTHORIZED", "Invalid or expired token")
    if "sub" not in data or "role" not in data:
        raise AppError(401, "UNAUTHORIZED", "Invalid token")
    return data
