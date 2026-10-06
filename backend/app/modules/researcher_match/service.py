import json

from app.core.access import researcher_ids
from app.core.db import new_id, now, transaction
from app.core.deps import CurrentUser
from app.core.errors import AppError
from app.core.notify import log_event, notify, notify_many


def score_researcher(required, skills, rating, availability) -> float:
    req, have = set(required), set(skills)
    overlap = (len(req & have) / len(req)) if req else 0.0
    return round(0.6 * overlap + 0.3 * (float(rating) / 5) + 0.1 * float(availability), 3)


def _overlap(required, skills) -> float:
    req = set(required)
    return (len(req & set(skills)) / len(req)) if req else 0.0


def problem_out(conn, row) -> dict:
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


def researcher_out(row) -> dict:
    return {
        "id": row["user_id"],
        "name": row["name"],
        "skills": json.loads(row["skills"] or "[]"),
        "rating": float(row["rating"]),
        "bio": row["bio"],
        "availability": float(row["availability"]),
    }


_RES_SQL = "SELECT r.*, u.name FROM researchers r JOIN users u ON u.id=r.user_id"


def owned_problem(conn, user: CurrentUser, problem_id: str):
    p = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    if not p:
        raise AppError(404, "NOT_FOUND", "Problem not found")
    if p["sponsor_id"] != user.id:
        raise AppError(403, "FORBIDDEN", "Only the owning sponsor can do this")
    return p


def matches(conn, user: CurrentUser, problem_id: str) -> list[dict]:
    p = owned_problem(conn, user, problem_id)
    required = json.loads(p["required_skills"] or "[]")
    excluded = {r["researcher_id"] for r in conn.execute("SELECT researcher_id FROM researcher_requests WHERE problem_id=?", (problem_id,))}
    excluded |= {
        r["researcher_id"]
        for r in conn.execute(
            "SELECT pr.researcher_id FROM project_researchers pr JOIN projects p ON p.id=pr.project_id WHERE p.problem_id=?", (problem_id,)
        )
    }
    out = []
    for row in conn.execute(_RES_SQL).fetchall():
        r = researcher_out(row)
        if r["id"] in excluded or _overlap(required, r["skills"]) == 0:
            continue
        out.append(
            {
                "researcher": r,
                "score": score_researcher(required, r["skills"], r["rating"], r["availability"]),
                "matched_skills": [s for s in required if s in r["skills"]],
                "missing_skills": [s for s in required if s not in r["skills"]],
            }
        )
    out.sort(key=lambda x: -x["score"])
    return out[:5]


def request_out(conn, row, problem=None) -> dict:
    if problem is None:
        problem = conn.execute("SELECT * FROM problems WHERE id=?", (row["problem_id"],)).fetchone()
    pout = problem_out(conn, problem)
    rname = conn.execute("SELECT name FROM users WHERE id=?", (row["researcher_id"],)).fetchone()
    project_id = None
    if row["status"] == "accepted":
        pr = conn.execute("SELECT id FROM projects WHERE problem_id=?", (row["problem_id"],)).fetchone()
        project_id = pr["id"] if pr else None
    return {
        "id": row["id"],
        "problem_id": row["problem_id"],
        "researcher_id": row["researcher_id"],
        "researcher_name": rname["name"] if rname else "",
        "sponsor_name": pout["sponsor_name"],
        "match_score": row["match_score"],
        "status": row["status"],
        "created_at": row["created_at"],
        "problem": pout,
        "project_id": project_id,
    }


def create_requests(conn, user: CurrentUser, problem_id: str, ids: list[str]) -> list[dict]:
    p = owned_problem(conn, user, problem_id)
    ids = list(dict.fromkeys(ids))
    if not 1 <= len(ids) <= 5:
        raise AppError(422, "VALIDATION_ERROR", "researcher_ids must contain 1-5 ids")
    required = json.loads(p["required_skills"] or "[]")
    created = []
    with transaction(conn):
        cur = conn.execute("SELECT status FROM problems WHERE id=?", (problem_id,)).fetchone()
        if cur["status"] not in ("open", "matched"):
            raise AppError(400, "BAD_STATE", "Problem is not open or matched")
        rows = []
        for rid in ids:
            row = conn.execute(_RES_SQL + " WHERE r.user_id=?", (rid,)).fetchone()
            if not row:
                raise AppError(404, "NOT_FOUND", "Researcher not found: " + rid)
            rows.append(row)
        for rid in ids:
            if conn.execute(
                "SELECT 1 FROM researcher_requests WHERE problem_id=? AND researcher_id=?", (problem_id, rid)
            ).fetchone():
                raise AppError(409, "CONFLICT", "A request already exists for researcher " + rid)
        for row in rows:
            r = researcher_out(row)
            rq = new_id()
            conn.execute(
                "INSERT INTO researcher_requests(id,problem_id,researcher_id,match_score,status,created_at) VALUES(?,?,?,?,?,?)",
                (rq, problem_id, r["id"], score_researcher(required, r["skills"], r["rating"], r["availability"]), "pending", now()),
            )
            notify(conn, r["id"], "researcher_request", "New project request", "You were invited to work on: " + p["title"], "/researcher/requests")
            created.append(rq)
    p = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    return [request_out(conn, conn.execute("SELECT * FROM researcher_requests WHERE id=?", (i,)).fetchone(), p) for i in created]


def problem_requests(conn, user: CurrentUser, problem_id: str) -> list[dict]:
    p = owned_problem(conn, user, problem_id)
    rows = conn.execute("SELECT * FROM researcher_requests WHERE problem_id=? ORDER BY created_at DESC", (problem_id,)).fetchall()
    return [request_out(conn, r, p) for r in rows]


def my_requests(conn, user: CurrentUser) -> list[dict]:
    rows = conn.execute("SELECT * FROM researcher_requests WHERE researcher_id=? ORDER BY created_at DESC", (user.id,)).fetchall()
    return [request_out(conn, r) for r in rows]


def respond(conn, user: CurrentUser, request_id: str, accept: bool) -> dict:
    req = conn.execute("SELECT * FROM researcher_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        raise AppError(404, "NOT_FOUND", "Request not found")
    if req["researcher_id"] != user.id:
        raise AppError(403, "FORBIDDEN", "This request is not addressed to you")
    if req["status"] != "pending":
        raise AppError(409, "CONFLICT", "Request is already " + req["status"])
    problem_id = req["problem_id"]
    project_id = None
    lost = False
    with transaction(conn):
        cur = conn.execute("SELECT status FROM researcher_requests WHERE id=?", (request_id,)).fetchone()
        if cur["status"] != "pending":
            raise AppError(409, "CONFLICT", "Request is already " + cur["status"])
        prob = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not accept:
            conn.execute("UPDATE researcher_requests SET status='declined' WHERE id=?", (request_id,))
            notify(conn, prob["sponsor_id"], "researcher_declined", "Request declined", user.name + " declined: " + prob["title"], "/problems/" + problem_id)
            return {"status": "declined", "project_id": None}
        if prob["status"] == "completed":
            conn.execute("UPDATE researcher_requests SET status='expired' WHERE id=?", (request_id,))
            lost = True
        else:
            proj = conn.execute("SELECT id FROM projects WHERE problem_id=?", (problem_id,)).fetchone()
            ts = now()
            if not proj:
                project_id = new_id()
                conn.execute(
                    "INSERT INTO projects(id,problem_id,researcher_id,status,created_at,completed_at) VALUES(?,?,?,?,?,NULL)",
                    (project_id, problem_id, user.id, "active", ts),
                )
                conn.execute(
                    "INSERT INTO project_researchers(project_id,researcher_id,role,share_pct,joined_at) VALUES(?,?,?,NULL,?)",
                    (project_id, user.id, "lead", ts),
                )
                conn.execute("UPDATE problems SET status='matched' WHERE id=?", (problem_id,))
                log_event(conn, project_id, user.id, "project_created", user.name + " started the project", project_id, {"researcher_id": user.id})
                notify(conn, prob["sponsor_id"], "researcher_accepted", "Researcher accepted", user.name + " accepted and started: " + prob["title"], "/projects/" + project_id)
            else:
                project_id = proj["id"]
                others = [i for i in researcher_ids(conn, project_id) if i != user.id]
                conn.execute(
                    "INSERT INTO project_researchers(project_id,researcher_id,role,share_pct,joined_at) VALUES(?,?,?,NULL,?)",
                    (project_id, user.id, "researcher", ts),
                )
                log_event(conn, project_id, user.id, "researcher_joined", user.name + " joined as co-researcher", user.id, {"researcher_id": user.id})
                notify_many(conn, [prob["sponsor_id"]] + others, "researcher_joined", "Co-researcher joined", user.name + " joined: " + prob["title"], "/projects/" + project_id)
            conn.execute("UPDATE researcher_requests SET status='accepted' WHERE id=?", (request_id,))
    if lost:
        raise AppError(409, "CONFLICT", "Problem is completed; request expired")
    return {"status": "accepted", "project_id": project_id}
