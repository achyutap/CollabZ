import json
import sqlite3

from app.core.db import new_id, now, transaction
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.core.skills import SKILL_IDS

from .schemas import RegisterIn

SEED_CREDIT = 500000.0


def _money(x) -> float:
    return round(float(x or 0), 2)


def _has_taken_quiz(conn: sqlite3.Connection, user_id: str, role: str) -> bool:
    if role != "student":
        return True
    return conn.execute("SELECT 1 FROM quiz_attempts WHERE student_id=? LIMIT 1", (user_id,)).fetchone() is not None


def _pending_skills(conn: sqlite3.Connection, user_id: str) -> list:
    r = conn.execute("SELECT pending_skills FROM students WHERE user_id=?", (user_id,)).fetchone()
    return json.loads(r["pending_skills"] or "[]") if r else []


def user_out(conn: sqlite3.Connection, row) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
        "name": row["name"],
        "email": row["email"],
        "has_taken_quiz": _has_taken_quiz(conn, row["id"], row["role"]),
        "pending_quiz_skills": _pending_skills(conn, row["id"]) if row["role"] == "student" else [],
    }


def _auth_response(conn: sqlite3.Connection, row) -> dict:
    return {
        "access_token": create_access_token(row["id"], row["role"]),
        "token_type": "bearer",
        "user": user_out(conn, row),
    }


def register(conn: sqlite3.Connection, body: RegisterIn) -> dict:
    email = str(body.email).strip().lower()
    name = body.name.strip()
    if not name:
        raise AppError(422, "VALIDATION_ERROR", "name: must not be empty")
    skills = []
    bio = (body.bio or "").strip()
    for s in body.skills or []:
        if s in SKILL_IDS and s not in skills:
            skills.append(s)
    if body.role == "researcher" and not skills:
        raise AppError(422, "VALIDATION_ERROR", "Researchers need at least one valid skill")
    uid = new_id()
    ts = now()
    try:
        with transaction(conn):
            if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                raise AppError(409, "CONFLICT", "Email already registered")
            conn.execute(
                "INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
                (uid, body.role, name, email, hash_password(body.password), ts),
            )
            if body.role == "researcher":
                conn.execute(
                    "INSERT INTO researchers(user_id, skills, rating, bio, availability) VALUES(?,?,3.0,?,1.0)",
                    (uid, json.dumps(skills), bio),
                )
            elif body.role == "student":
                conn.execute(
                    "INSERT INTO students(user_id, skills, temp_rating, final_rating, projects_done, last_active_at, pending_skills) "
                    "VALUES(?,?,NULL,NULL,0,?,?)",
                    (uid, "[]", ts, json.dumps(skills if body.role == "student" else [])),
                )
            conn.execute("INSERT INTO profiles(user_id, updated_at) VALUES(?,?)", (uid, ts))
            balance = SEED_CREDIT if body.role == "sponsor" else 0.0
            conn.execute("INSERT INTO wallets(user_id, balance) VALUES(?,?)", (uid, balance))
            if body.role == "sponsor":
                conn.execute(
                    "INSERT INTO ledger_entries(id, user_id, problem_id, project_id, amount, type, created_at) "
                    "VALUES(?,?,NULL,NULL,?, 'seed', ?)",
                    (new_id(), uid, SEED_CREDIT, ts),
                )
    except sqlite3.IntegrityError:
        raise AppError(409, "CONFLICT", "Email already registered")
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return _auth_response(conn, row)


def login(conn: sqlite3.Connection, email: str, password: str) -> dict:
    row = conn.execute("SELECT * FROM users WHERE email=?", ((email or "").strip().lower(),)).fetchone()
    if row is None or not verify_password(password or "", row["password_hash"]):
        raise AppError(401, "UNAUTHORIZED", "Invalid email or password")
    if row["is_blacklisted"]:
        raise AppError(403, "BLACKLISTED", "Your account has been blocked due to repeated plagiarism.")
    return _auth_response(conn, row)


def me(conn: sqlite3.Connection, user_id: str) -> dict:
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if row is None:
        raise AppError(401, "UNAUTHORIZED", "User not found")
    return user_out(conn, row)


def get_researcher(conn: sqlite3.Connection, rid: str) -> dict:
    row = conn.execute(
        "SELECT u.id, u.name, r.skills, r.rating, r.bio, r.availability FROM users u "
        "JOIN researchers r ON r.user_id=u.id WHERE u.id=? AND u.role='researcher'",
        (rid,),
    ).fetchone()
    if row is None:
        raise AppError(404, "NOT_FOUND", "Researcher not found")
    return {
        "id": row["id"],
        "name": row["name"],
        "skills": json.loads(row["skills"] or "[]"),
        "rating": row["rating"],
        "bio": row["bio"],
        "availability": row["availability"],
    }


def get_student(conn: sqlite3.Connection, sid: str, requester_id: str = None) -> dict:
    row = conn.execute(
        "SELECT u.id, u.name, s.skills, s.temp_rating, s.final_rating, s.projects_done, s.pending_skills FROM users u "
        "JOIN students s ON s.user_id=u.id WHERE u.id=? AND u.role='student'",
        (sid,),
    ).fetchone()
    if row is None:
        raise AppError(404, "NOT_FOUND", "Student not found")
    done = row["projects_done"]
    if done == 0:
        rating, rtype = row["temp_rating"], "temp"
    else:
        rating, rtype = row["final_rating"], "final"
    if rating is None:
        rtype = None
    return {
        "id": row["id"],
        "name": row["name"],
        "skills": json.loads(row["skills"] or "[]"),
        "temp_rating": row["temp_rating"],
        "final_rating": row["final_rating"],
        "rating": rating,
        "rating_type": rtype,
        "projects_done": done,
        "pending_skills": json.loads(row["pending_skills"] or "[]") if requester_id == row["id"] else [],
    }


def wallet(conn: sqlite3.Connection, user_id: str) -> dict:
    w = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (user_id,)).fetchone()
    rows = conn.execute(
        "SELECT id, amount, type, problem_id, project_id, created_at FROM ledger_entries "
        "WHERE user_id=? ORDER BY created_at DESC, rowid DESC LIMIT 20",
        (user_id,),
    ).fetchall()
    return {
        "balance": _money(w["balance"]) if w else 0.0,
        "entries": [
            {
                "id": r["id"],
                "amount": _money(r["amount"]),
                "type": r["type"],
                "problem_id": r["problem_id"],
                "project_id": r["project_id"],
                "created_at": r["created_at"],
            }
            for r in rows
        ],
    }
