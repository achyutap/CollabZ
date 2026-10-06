import json
from datetime import datetime, timezone

from app.core.access import require_project_access, researcher_ids
from app.core.db import new_id, now, transaction
from app.core.deps import CurrentUser
from app.core.errors import AppError
from app.core.notify import log_event, notify, notify_many
from app.core.skills import SKILL_IDS

RESEARCHER_ROLES = {"lead", "researcher"}


def _dt(v) -> datetime:
    d = v if isinstance(v, datetime) else datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def score_student(has_skill, rating, last_active_at, now) -> float:
    days = max(0.0, (_dt(now) - _dt(last_active_at)).total_seconds() / 86400)
    recency = 1 - min(days, 90) / 90
    r = float(rating) if rating is not None else 0.0
    return round(0.5 * (1 if has_skill else 0) + 0.4 * (r / 5) + 0.1 * recency, 3)


def rating_of(temp, final, done):
    if (done or 0) == 0:
        return temp, ("temp" if temp is not None else None)
    return final, ("final" if final is not None else None)


def student_out(row) -> dict:
    rating, rtype = rating_of(row["temp_rating"], row["final_rating"], row["projects_done"])
    return {
        "id": row["user_id"],
        "name": row["name"],
        "skills": json.loads(row["skills"] or "[]"),
        "pending_skills": [],  # only filled for the student themself; requesters here are researchers
        "temp_rating": row["temp_rating"],
        "final_rating": row["final_rating"],
        "rating": rating,
        "rating_type": rtype,
        "projects_done": int(row["projects_done"]),
    }


_STU_SQL = "SELECT s.*, u.name, u.is_blacklisted FROM students s JOIN users u ON u.id=s.user_id"


def _project(conn, user: CurrentUser, project_id: str):
    require_project_access(conn, project_id, user, RESEARCHER_ROLES)
    return conn.execute(
        "SELECT pr.*, p.title FROM projects pr JOIN problems p ON p.id=pr.problem_id WHERE pr.id=?", (project_id,)
    ).fetchone()


def _filled(conn, project_id, skill) -> int:
    return conn.execute(
        "SELECT COUNT(*) c FROM project_members WHERE project_id=? AND skill=? AND status='active'", (project_id, skill)
    ).fetchone()["c"]


def _active_ids(conn, project_id) -> set:
    return {r["student_id"] for r in conn.execute("SELECT student_id FROM project_members WHERE project_id=? AND status='active'", (project_id,))}


def request_out(conn, row) -> dict:
    pr = conn.execute(
        "SELECT p.title, u.name AS rname FROM projects pr JOIN problems p ON p.id=pr.problem_id "
        "JOIN users u ON u.id=pr.researcher_id WHERE pr.id=?",
        (row["project_id"],),
    ).fetchone()
    st = conn.execute("SELECT name FROM users WHERE id=?", (row["student_id"],)).fetchone()
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "project_title": pr["title"] if pr else "",
        "researcher_name": pr["rname"] if pr else "",
        "student_id": row["student_id"],
        "student_name": st["name"] if st else "",
        "skill": row["skill"],
        "match_score": row["match_score"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def _eligible(conn, project_id: str):
    active = _active_ids(conn, project_id)
    return [r for r in conn.execute(_STU_SQL).fetchall() if not r["is_blacklisted"] and r["user_id"] not in active]


def shortlist(conn, user: CurrentUser, project_id: str) -> list[dict]:
    _project(conn, user, project_id)
    needs = conn.execute("SELECT skill,count FROM skill_needs WHERE project_id=? ORDER BY rowid", (project_id,)).fetchall()
    students = _eligible(conn, project_id)
    ts = now()
    out = []
    for n in needs:
        cands = []
        for row in students:
            s = student_out(row)
            if n["skill"] not in s["skills"] or s["rating"] is None:
                continue
            rs = conn.execute(
                "SELECT status FROM student_requests WHERE project_id=? AND student_id=? AND skill=?", (project_id, s["id"], n["skill"])
            ).fetchone()
            cands.append(
                {
                    "student": s,
                    "score": score_student(True, s["rating"], row["last_active_at"], ts),
                    "rating": s["rating"],
                    "rating_type": s["rating_type"],
                    "projects_done": s["projects_done"],
                    "request_status": rs["status"] if rs else None,
                }
            )
        cands.sort(key=lambda c: -c["score"])
        out.append(
            {"skill": n["skill"], "count": int(n["count"]), "filled": _filled(conn, project_id, n["skill"]), "candidates": cands[: 2 * int(n["count"])]}
        )
    return out


def search(conn, user: CurrentUser, project_id: str, q: str | None, skill: str | None) -> list[dict]:
    _project(conn, user, project_id)
    if skill and skill not in SKILL_IDS:
        raise AppError(422, "VALIDATION_ERROR", "Unknown skill")
    needle = (q or "").strip().lower()
    res = []
    for row in _eligible(conn, project_id):
        s = student_out(row)
        if skill and skill not in s["skills"]:
            continue
        if needle and needle not in s["name"].lower() and not any(needle in k.lower() for k in s["skills"]):
            continue
        res.append(s)
    res.sort(key=lambda s: (-(s["rating"] if s["rating"] is not None else -1), s["name"].lower()))
    return res[:20]


def create_request(conn, user: CurrentUser, project_id: str, student_id: str, skill: str) -> dict:
    proj = _project(conn, user, project_id)
    rid = None
    with transaction(conn):
        need = conn.execute("SELECT count FROM skill_needs WHERE project_id=? AND skill=?", (project_id, skill)).fetchone()
        if not need:
            raise AppError(400, "BAD_STATE", "Add this skill to the project's skill needs first")
        row = conn.execute(_STU_SQL + " WHERE s.user_id=?", (student_id,)).fetchone()
        if not row:
            raise AppError(404, "NOT_FOUND", "Student not found")
        if row["is_blacklisted"]:
            raise AppError(400, "BAD_STATE", "Student is not available")
        s = student_out(row)
        if skill not in s["skills"]:
            raise AppError(400, "VALIDATION_ERROR", "Student does not have this verified skill")
        if student_id in _active_ids(conn, project_id):
            raise AppError(409, "CONFLICT", "Student is already a member")
        ex = conn.execute(
            "SELECT id,status FROM student_requests WHERE project_id=? AND student_id=? AND skill=?", (project_id, student_id, skill)
        ).fetchone()
        if ex and ex["status"] == "pending":
            raise AppError(409, "CONFLICT", "A pending request already exists")
        if _filled(conn, project_id, skill) >= need["count"]:
            raise AppError(400, "BAD_STATE", "Slots full")
        score = score_student(True, s["rating"], row["last_active_at"], now())
        if ex:  # declined / expired / accepted-then-removed: re-invite reuses the row (UNIQUE constraint)
            rid = ex["id"]
            conn.execute("UPDATE student_requests SET status='pending', match_score=?, created_at=? WHERE id=?", (score, now(), rid))
        else:
            rid = new_id()
            conn.execute(
                "INSERT INTO student_requests(id,project_id,student_id,skill,match_score,status,created_at) VALUES(?,?,?,?,?,?,?)",
                (rid, project_id, student_id, skill, score, "pending", now()),
            )
        notify(conn, student_id, "student_request", "Project invitation", f"You were invited to join {proj['title']} as {skill}", "/student/requests")
    return request_out(conn, conn.execute("SELECT * FROM student_requests WHERE id=?", (rid,)).fetchone())


def project_requests(conn, user: CurrentUser, project_id: str) -> list[dict]:
    _project(conn, user, project_id)
    rows = conn.execute("SELECT * FROM student_requests WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
    return [request_out(conn, r) for r in rows]


def my_requests(conn, user: CurrentUser) -> list[dict]:
    rows = conn.execute("SELECT * FROM student_requests WHERE student_id=? ORDER BY created_at DESC", (user.id,)).fetchall()
    return [request_out(conn, r) for r in rows]


def respond(conn, user: CurrentUser, request_id: str, accept: bool) -> dict:
    req = conn.execute("SELECT * FROM student_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        raise AppError(404, "NOT_FOUND", "Request not found")
    if req["student_id"] != user.id:
        raise AppError(403, "FORBIDDEN", "This request is not addressed to you")
    if req["status"] != "pending":
        raise AppError(409, "CONFLICT", "Request is already " + req["status"])
    pid, skill = req["project_id"], req["skill"]
    lost = False
    with transaction(conn):
        cur = conn.execute("SELECT status FROM student_requests WHERE id=?", (request_id,)).fetchone()
        if cur["status"] != "pending":
            raise AppError(409, "CONFLICT", "Request is already " + cur["status"])
        title = conn.execute("SELECT p.title FROM projects pr JOIN problems p ON p.id=pr.problem_id WHERE pr.id=?", (pid,)).fetchone()["title"]
        rids = researcher_ids(conn, pid)
        if not accept:
            conn.execute("UPDATE student_requests SET status='declined' WHERE id=?", (request_id,))
            notify_many(conn, rids, "student_declined", "Invitation declined", f"{user.name} declined to join {title} ({skill})", f"/projects/{pid}")
            return {"status": "declined"}
        need = conn.execute("SELECT count FROM skill_needs WHERE project_id=? AND skill=?", (pid, skill)).fetchone()
        filled = _filled(conn, pid, skill)
        if not need or filled >= need["count"]:
            conn.execute("UPDATE student_requests SET status='expired' WHERE id=?", (request_id,))
            lost = True
        else:
            m = conn.execute("SELECT status FROM project_members WHERE project_id=? AND student_id=?", (pid, user.id)).fetchone()
            ts = now()
            if m and m["status"] == "active":
                raise AppError(409, "CONFLICT", "You are already a member of this project")
            if m and m["status"] == "blacklisted":
                raise AppError(409, "CONFLICT", "You cannot rejoin this project")
            if m:
                conn.execute(
                    "UPDATE project_members SET status='active', skill=?, removed_at=NULL, removed_reason=NULL, joined_at=? WHERE project_id=? AND student_id=?",
                    (skill, ts, pid, user.id),
                )
            else:
                conn.execute(
                    "INSERT INTO project_members(project_id,student_id,skill,status,joined_at) VALUES(?,?,?,'active',?)", (pid, user.id, skill, ts)
                )
            conn.execute("UPDATE student_requests SET status='accepted' WHERE id=?", (request_id,))
            conn.execute("UPDATE students SET last_active_at=? WHERE user_id=?", (ts, user.id))
            if filled + 1 >= need["count"]:
                conn.execute("UPDATE student_requests SET status='expired' WHERE project_id=? AND skill=? AND status='pending'", (pid, skill))
            log_event(conn, pid, user.id, "student_joined", f"{user.name} joined as {skill}", user.id, {"student_id": user.id, "skill": skill})
            notify_many(conn, rids, "student_joined", "Student joined", f"{user.name} joined {title} ({skill})", f"/projects/{pid}")
    if lost:
        raise AppError(409, "CONFLICT", "All slots for this skill are filled; request expired")
    return {"status": "accepted"}
