import sqlite3
from typing import Optional

from app.core.errors import AppError


def sponsor_id(conn: sqlite3.Connection, project_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT pr.sponsor_id AS sid FROM projects p JOIN problems pr ON pr.id=p.problem_id WHERE p.id=?",
        (project_id,),
    ).fetchone()
    return row["sid"] if row else None


def lead_id(conn: sqlite3.Connection, project_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT researcher_id FROM project_researchers WHERE project_id=? AND role='lead'", (project_id,)
    ).fetchone()
    if row:
        return row["researcher_id"]
    row = conn.execute("SELECT researcher_id FROM projects WHERE id=?", (project_id,)).fetchone()
    return row["researcher_id"] if row else None


def researcher_ids(conn: sqlite3.Connection, project_id: str) -> list:
    rows = conn.execute(
        "SELECT researcher_id FROM project_researchers WHERE project_id=? "
        "ORDER BY CASE role WHEN 'lead' THEN 0 ELSE 1 END, joined_at, rowid",
        (project_id,),
    ).fetchall()
    ids = [r["researcher_id"] for r in rows]
    if not ids:
        lid = lead_id(conn, project_id)
        return [lid] if lid else []
    return ids


def active_student_ids(conn: sqlite3.Connection, project_id: str) -> list:
    rows = conn.execute(
        "SELECT student_id FROM project_members WHERE project_id=? AND status='active' ORDER BY rowid",
        (project_id,),
    ).fetchall()
    return [r["student_id"] for r in rows]


def is_project_researcher(conn: sqlite3.Connection, project_id: str, user_id: str) -> bool:
    return user_id in researcher_ids(conn, project_id)


def project_role(conn: sqlite3.Connection, project_id: str, user_id: str) -> Optional[str]:
    if not user_id:
        return None
    if sponsor_id(conn, project_id) == user_id:
        return "sponsor"
    if lead_id(conn, project_id) == user_id:
        return "lead"
    if is_project_researcher(conn, project_id, user_id):
        return "researcher"
    row = conn.execute(
        "SELECT 1 FROM project_members WHERE project_id=? AND student_id=? AND status='active'",
        (project_id, user_id),
    ).fetchone()
    return "student" if row else None


def require_project_access(conn: sqlite3.Connection, project_id: str, user, roles: Optional[set] = None) -> str:
    if conn.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone() is None:
        raise AppError(404, "NOT_FOUND", "Project not found")
    role = project_role(conn, project_id, user.id)
    if role is None or (roles is not None and role not in roles):
        raise AppError(403, "FORBIDDEN", "You do not have access to this project")
    return role
