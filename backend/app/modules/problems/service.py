import json
import sqlite3

from app.core.db import new_id, now, transaction
from app.core.deps import CurrentUser
from app.core.errors import AppError
from app.core.llm import LLMUnavailable, complete_json
from app.core.skills import SKILL_IDS, SKILLS


def problem_out(conn: sqlite3.Connection, row) -> dict:
    s = conn.execute("SELECT name FROM users WHERE id=?", (row["sponsor_id"],)).fetchone()
    return {
        "id": row["id"],
        "sponsor_id": row["sponsor_id"],
        "sponsor_name": s["name"] if s else "",
        "title": row["title"],
        "description": row["description"],
        "budget": round(float(row["budget"]), 2),
        "student_pct": int(row["student_pct"]),
        "researcher_pct": int(row["researcher_pct"]),
        "project_pct": int(row["project_pct"]),
        "required_skills": json.loads(row["required_skills"] or "[]"),
        "status": row["status"],
        "created_at": row["created_at"],
    }


def get_problem_row(conn, problem_id: str):
    row = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    if not row:
        raise AppError(404, "NOT_FOUND", "Problem not found")
    return row


def resolve_pcts(student_pct: int, researcher_pct, project_pct) -> tuple[int, int]:
    pp = 0 if project_pct is None else project_pct
    rp = 100 - student_pct - pp if researcher_pct is None else researcher_pct
    if rp < 0 or student_pct + rp + pp != 100:
        raise AppError(422, "VALIDATION_ERROR", "student_pct + researcher_pct + project_pct must equal 100")
    return rp, pp


def keyword_skills(title: str, description: str) -> list[str]:
    text = (title + " " + description).lower()
    scored = []
    for sk in SKILLS:
        terms = {a.lower() for a in sk.get("aliases", [])} | {sk["id"].lower()}
        count = sum(text.count(t) for t in terms if t)
        if count > 0:
            scored.append((count, sk["id"]))
    scored.sort(key=lambda x: -x[0])
    out = [sid for _, sid in scored[:5]]
    return out or ["data_analysis"]


def extract_skills(title: str, description: str) -> list[str]:
    system = (
        "Select the skills required to solve this problem ONLY from this taxonomy: "
        + ", ".join(SKILL_IDS)
        + '. Return JSON {"required_skills": [2-6 ids]}'
    )
    try:
        data = complete_json(system, "Title: " + title + "\n\nDescription: " + description)
        raw = data.get("required_skills") if isinstance(data, dict) else None
        out: list[str] = []
        if isinstance(raw, list):
            for s in raw:
                if isinstance(s, str) and s in SKILL_IDS and s not in out:
                    out.append(s)
        out = out[:6]
        if out:
            return out
    except LLMUnavailable:
        pass
    return keyword_skills(title, description)


def _balance(conn, user_id: str) -> float:
    w = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (user_id,)).fetchone()
    return float(w["balance"]) if w else 0.0


def create_problem(conn, user: CurrentUser, body) -> dict:
    rp, pp = resolve_pcts(body.student_pct, body.researcher_pct, body.project_pct)
    budget = round(float(body.budget), 2)
    if _balance(conn, user.id) < budget:
        raise AppError(400, "INSUFFICIENT_FUNDS", "Wallet balance is lower than the budget")
    skills = extract_skills(body.title, body.description)
    pid = new_id()
    ts = now()
    with transaction(conn):
        bal = _balance(conn, user.id)
        if bal < budget:
            raise AppError(400, "INSUFFICIENT_FUNDS", "Wallet balance is lower than the budget")
        conn.execute("UPDATE wallets SET balance=? WHERE user_id=?", (round(bal - budget, 2), user.id))
        conn.execute(
            "INSERT INTO ledger_entries(id,user_id,problem_id,project_id,amount,type,created_at) VALUES(?,?,?,NULL,?,?,?)",
            (new_id(), user.id, pid, -budget, "escrow", ts),
        )
        conn.execute(
            "INSERT INTO problems(id,sponsor_id,title,description,budget,student_pct,researcher_pct,project_pct,required_skills,status,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (pid, user.id, body.title.strip(), body.description, budget, body.student_pct, rp, pp, json.dumps(skills), "open", ts),
        )
    return problem_out(conn, get_problem_row(conn, pid))


def list_problems(conn, user: CurrentUser) -> list[dict]:
    if user.role == "sponsor":
        rows = conn.execute("SELECT * FROM problems WHERE sponsor_id=? ORDER BY created_at DESC", (user.id,)).fetchall()
    elif user.role == "researcher":
        rows = conn.execute(
            "SELECT p.* FROM problems p WHERE p.id IN (SELECT problem_id FROM researcher_requests WHERE researcher_id=?) ORDER BY p.created_at DESC",
            (user.id,),
        ).fetchall()
    else:
        raise AppError(403, "FORBIDDEN", "Not allowed")
    return [problem_out(conn, r) for r in rows]


def get_problem(conn, user: CurrentUser, problem_id: str) -> dict:
    row = get_problem_row(conn, problem_id)
    if user.role == "sponsor" and row["sponsor_id"] == user.id:
        return problem_out(conn, row)
    if user.role == "researcher":
        r = conn.execute(
            "SELECT 1 FROM researcher_requests WHERE problem_id=? AND researcher_id=?", (problem_id, user.id)
        ).fetchone()
        if not r:
            r = conn.execute(
                "SELECT 1 FROM project_researchers pr JOIN projects p ON p.id=pr.project_id WHERE p.problem_id=? AND pr.researcher_id=?",
                (problem_id, user.id),
            ).fetchone()
        if r:
            return problem_out(conn, row)
    raise AppError(403, "FORBIDDEN", "Not allowed to view this problem")


def patch_skills(conn, user: CurrentUser, problem_id: str, skills: list[str]) -> dict:
    row = get_problem_row(conn, problem_id)
    if row["sponsor_id"] != user.id:
        raise AppError(403, "FORBIDDEN", "Only the owning sponsor can edit skills")
    if len(skills) < 1 or len(skills) > 8 or len(set(skills)) != len(skills) or any(s not in SKILL_IDS for s in skills):
        raise AppError(422, "VALIDATION_ERROR", "required_skills must be 1-8 unique taxonomy ids")
    with transaction(conn):
        cur = conn.execute("SELECT status FROM problems WHERE id=?", (problem_id,)).fetchone()
        if cur["status"] != "open":
            raise AppError(400, "BAD_STATE", "Skills can only be edited while the problem is open")
        conn.execute("UPDATE problems SET required_skills=? WHERE id=?", (json.dumps(skills), problem_id))
    return problem_out(conn, get_problem_row(conn, problem_id))
