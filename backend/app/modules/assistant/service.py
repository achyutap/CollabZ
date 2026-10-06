import json
from datetime import datetime, timedelta, timezone

from app.core.access import require_project_access
from app.core.db import new_id, now, transaction
from app.core.errors import AppError
from app.core.llm import LLMUnavailable, complete

RATE_LIMIT = 20
RATE_WINDOW_MIN = 60
HISTORY_WINDOW = 10
ROLE_LABEL = {"sponsor": "sponsor", "lead": "researcher", "researcher": "researcher", "student": "student"}


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _project_info(conn, project_id: str):
    return conn.execute(
        "SELECT pr.title, pr.description, pr.required_skills FROM projects p JOIN problems pr ON pr.id = p.problem_id WHERE p.id=?",
        (project_id,),
    ).fetchone()


def _system_prompt(info, role_label: str) -> str:
    skills = ", ".join(json.loads(info["required_skills"] or "[]"))
    return (
        f"You are the project assistant for '{info['title']}'. Description: {info['description']}. "
        f"Required skills: {skills}. The user is a {role_label}. "
        "Help with the project: explain concepts, review ideas, suggest approaches. "
        "Do not write complete deliverables meant to be handed in as original research; guide instead. Be concise."
    )


def _recent_user_count(conn, project_id: str, user_id: str) -> int:
    rows = conn.execute(
        "SELECT created_at FROM chat_messages WHERE project_id=? AND user_id=? AND role='user' ORDER BY created_at DESC, rowid DESC LIMIT 100",
        (project_id, user_id),
    ).fetchall()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=RATE_WINDOW_MIN)
    count = 0
    for r in rows:
        try:
            if _parse(r["created_at"]) >= cutoff:
                count += 1
        except ValueError:
            continue
    return count


def send(conn, project_id: str, user, message: str) -> dict:
    role = require_project_access(conn, project_id, user)
    message = (message or "").strip()
    if not (1 <= len(message) <= 2000):
        raise AppError(422, "VALIDATION_ERROR", "Message must be 1-2000 characters")
    if _recent_user_count(conn, project_id, user.id) >= RATE_LIMIT:
        raise AppError(429, "RATE_LIMITED", "Too many messages. Try again later.")
    info = _project_info(conn, project_id)
    if info is None:
        raise AppError(404, "NOT_FOUND", "Project not found")
    rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE project_id=? AND user_id=? ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (project_id, user.id, HISTORY_WINDOW),
    ).fetchall()[::-1]
    history = "".join(f"{'User' if r['role'] == 'user' else 'Assistant'}: {r['content']}\n" for r in rows)
    prompt = history + f"User: {message}"
    try:
        reply = complete(_system_prompt(info, ROLE_LABEL.get(role, "student")), prompt, cache=False)
    except LLMUnavailable:
        raise AppError(503, "LLM_UNAVAILABLE", "The assistant is unavailable right now")
    with transaction(conn):
        conn.execute(
            "INSERT INTO chat_messages(id, project_id, user_id, role, content, created_at) VALUES(?,?,?,?,?,?)",
            (new_id(), project_id, user.id, "user", message, now()),
        )
        conn.execute(
            "INSERT INTO chat_messages(id, project_id, user_id, role, content, created_at) VALUES(?,?,?,?,?,?)",
            (new_id(), project_id, user.id, "assistant", reply, now()),
        )
    return {"reply": reply}


def history(conn, project_id: str, user) -> list[dict]:
    require_project_access(conn, project_id, user)
    rows = conn.execute(
        "SELECT id, role, content, created_at FROM chat_messages WHERE project_id=? AND user_id=? ORDER BY created_at DESC, rowid DESC LIMIT 100",
        (project_id, user.id),
    ).fetchall()[::-1]
    return [{"id": r["id"], "role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in rows]
