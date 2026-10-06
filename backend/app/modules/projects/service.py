import json

from app.core.access import require_project_access
from app.core.db import new_id, now, transaction
from app.core.deps import CurrentUser
from app.core.errors import AppError
from app.core.notify import log_event, notify, notify_many
from app.core.skills import SKILL_IDS

RESEARCHER_ROLES = {"lead", "researcher"}


def student_rating(temp, final, done):
    return temp if (done or 0) == 0 else final


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


_PROJ_SQL = (
    "SELECT pr.id, pr.problem_id, pr.researcher_id, pr.status, pr.created_at, p.title, p.sponsor_id, "
    "u.name AS researcher_name, su.name AS sponsor_name, "
    "(SELECT COUNT(*) FROM project_members m WHERE m.project_id=pr.id AND m.status='active') AS member_count "
    "FROM projects pr JOIN problems p ON p.id=pr.problem_id "
    "JOIN users u ON u.id=pr.researcher_id JOIN users su ON su.id=p.sponsor_id "
)


def researchers_of(conn, project_id: str):
    return conn.execute(
        "SELECT x.researcher_id, x.role, x.share_pct, u.name FROM project_researchers x JOIN users u ON u.id=x.researcher_id "
        "WHERE x.project_id=? ORDER BY CASE x.role WHEN 'lead' THEN 0 ELSE 1 END, x.joined_at",
        (project_id,),
    ).fetchall()


def effective_shares(rows) -> list[float]:
    """Stored shares when every researcher has one, else equal split (remainder to the lead, who is first)."""
    n = len(rows)
    if n and all(r["share_pct"] is not None for r in rows):
        return [round(float(r["share_pct"]), 2) for r in rows]
    if not n:
        return []
    base = round(100 / n, 2)
    shares = [base] * n
    shares[0] = round(100 - base * (n - 1), 2)
    return shares


def project_out(conn, row) -> dict:
    return {
        "id": row["id"],
        "problem_id": row["problem_id"],
        "title": row["title"],
        "status": row["status"],
        "researcher": {"id": row["researcher_id"], "name": row["researcher_name"]},
        "researchers": [{"id": r["researcher_id"], "name": r["name"], "role": r["role"]} for r in researchers_of(conn, row["id"])],
        "sponsor_name": row["sponsor_name"],
        "member_count": int(row["member_count"]),
        "created_at": row["created_at"],
    }


def list_projects(conn, user: CurrentUser) -> list[dict]:
    if user.role == "sponsor":
        rows = conn.execute(_PROJ_SQL + "WHERE p.sponsor_id=? ORDER BY pr.created_at DESC", (user.id,)).fetchall()
    elif user.role == "researcher":
        rows = conn.execute(
            _PROJ_SQL + "WHERE pr.id IN (SELECT project_id FROM project_researchers WHERE researcher_id=?) ORDER BY pr.created_at DESC",
            (user.id,),
        ).fetchall()
    else:
        rows = conn.execute(
            _PROJ_SQL + "WHERE pr.id IN (SELECT project_id FROM project_members WHERE student_id=? AND status='active') ORDER BY pr.created_at DESC",
            (user.id,),
        ).fetchall()
    return [project_out(conn, r) for r in rows]


def _row(conn, project_id: str):
    row = conn.execute(_PROJ_SQL + "WHERE pr.id=?", (project_id,)).fetchone()
    if not row:
        raise AppError(404, "NOT_FOUND", "Project not found")
    return row


def _needs(conn, project_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT n.skill, n.count, (SELECT COUNT(*) FROM project_members m WHERE m.project_id=n.project_id AND m.skill=n.skill AND m.status='active') AS filled "
        "FROM skill_needs n WHERE n.project_id=? ORDER BY n.rowid",
        (project_id,),
    ).fetchall()
    return [{"skill": r["skill"], "count": int(r["count"]), "filled": int(r["filled"])} for r in rows]


def get_detail(conn, user: CurrentUser, project_id: str) -> dict:
    my_role = require_project_access(conn, project_id, user)
    row = _row(conn, project_id)
    prob = conn.execute("SELECT * FROM problems WHERE id=?", (row["problem_id"],)).fetchone()
    members = []
    for m in conn.execute(
        "SELECT m.student_id, m.skill, u.name, s.temp_rating, s.final_rating, s.projects_done "
        "FROM project_members m JOIN users u ON u.id=m.student_id JOIN students s ON s.user_id=m.student_id "
        "WHERE m.project_id=? AND m.status='active' ORDER BY u.name",
        (project_id,),
    ).fetchall():
        members.append(
            {
                "student_id": m["student_id"],
                "name": m["name"],
                "skill": m["skill"],
                "rating": student_rating(m["temp_rating"], m["final_rating"], m["projects_done"]),
            }
        )
    rrows = researchers_of(conn, project_id)
    shares = effective_shares(rrows)
    total = float(prob["budget"])
    pool = total * int(prob["student_pct"]) / 100
    rpool = total * int(prob["researcher_pct"]) / 100
    fund = total - pool - rpool
    out = project_out(conn, row)
    out.update(
        {
            "problem": problem_out(conn, prob),
            "skill_needs": _needs(conn, project_id),
            "members": members,
            "researchers": [
                {"id": r["researcher_id"], "name": r["name"], "role": r["role"], "share_pct": shares[i]} for i, r in enumerate(rrows)
            ],
            "budget": {
                "total": round(total, 2),
                "student_pool": round(pool, 2),
                "researcher_pool": round(rpool, 2),
                "project_fund": round(fund, 2),
                "researcher_share": round(rpool, 2),
            },
            "my_role": my_role,
            "can_manage": my_role in RESEARCHER_ROLES and row["status"] == "active",
        }
    )
    return out


def set_skill_needs(conn, user: CurrentUser, project_id: str, items) -> list[dict]:
    require_project_access(conn, project_id, user, RESEARCHER_ROLES)
    if not items:
        raise AppError(422, "VALIDATION_ERROR", "At least one skill need is required")
    skills = [i.skill for i in items]
    if any(s not in SKILL_IDS for s in skills):
        raise AppError(422, "VALIDATION_ERROR", "Unknown skill")
    if len(set(skills)) != len(skills):
        raise AppError(422, "VALIDATION_ERROR", "Duplicate skills")
    with transaction(conn):
        cur = conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()
        if cur["status"] != "active":
            raise AppError(400, "BAD_STATE", "Project is not active")
        has_requests = conn.execute("SELECT 1 FROM student_requests WHERE project_id=? LIMIT 1", (project_id,)).fetchone()
        filled = {
            r["skill"]: r["c"]
            for r in conn.execute(
                "SELECT skill, COUNT(*) c FROM project_members WHERE project_id=? AND status='active' GROUP BY skill", (project_id,)
            ).fetchall()
        }
        for i in items:
            if i.count < filled.get(i.skill, 0):
                raise AppError(400, "BAD_STATE", f"Count for {i.skill} cannot be below filled slots ({filled[i.skill]})")
        if not has_requests:
            conn.execute("DELETE FROM skill_needs WHERE project_id=?", (project_id,))
        for i in items:
            ex = conn.execute("SELECT id FROM skill_needs WHERE project_id=? AND skill=?", (project_id, i.skill)).fetchone()
            if ex:
                conn.execute("UPDATE skill_needs SET count=? WHERE id=?", (i.count, ex["id"]))
            else:
                conn.execute("INSERT INTO skill_needs(id,project_id,skill,count) VALUES(?,?,?,?)", (new_id(), project_id, i.skill, i.count))
    return _needs(conn, project_id)


def remove_member(conn, user: CurrentUser, project_id: str, student_id: str) -> dict:
    require_project_access(conn, project_id, user, RESEARCHER_ROLES)
    title = _row(conn, project_id)["title"]
    with transaction(conn):
        if conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()["status"] != "active":
            raise AppError(400, "BAD_STATE", "Project is not active")
        m = conn.execute("SELECT status FROM project_members WHERE project_id=? AND student_id=?", (project_id, student_id)).fetchone()
        if not m or m["status"] != "active":
            raise AppError(404, "NOT_FOUND", "Active member not found")
        ts = now()
        conn.execute(
            "UPDATE project_members SET status='removed', removed_at=?, removed_reason='removed_by_researcher' WHERE project_id=? AND student_id=?",
            (ts, project_id, student_id),
        )
        conn.execute(
            "UPDATE student_requests SET status='expired' WHERE project_id=? AND student_id=? AND status='pending'", (project_id, student_id)
        )
        st = conn.execute("SELECT name FROM users WHERE id=?", (student_id,)).fetchone()
        notify(conn, student_id, "removed_from_project", "Removed from project", "You were removed from: " + title, "/projects/" + project_id)
        log_event(
            conn, project_id, user.id, "student_removed", (st["name"] if st else "A student") + " was removed from the project",
            student_id, {"student_id": student_id},
        )
    return {"status": "removed"}


def set_shares(conn, user: CurrentUser, project_id: str, items) -> list[dict]:
    require_project_access(conn, project_id, user, {"lead"})
    title = _row(conn, project_id)["title"]
    with transaction(conn):
        if conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()["status"] != "active":
            raise AppError(400, "BAD_STATE", "Project is not active")
        rrows = researchers_of(conn, project_id)
        ids = [i.researcher_id for i in items]
        if len(set(ids)) != len(ids) or set(ids) != {r["researcher_id"] for r in rrows}:
            raise AppError(422, "VALIDATION_ERROR", "Shares must list every project researcher exactly once")
        if abs(sum(i.share_pct for i in items) - 100) > 0.01:
            raise AppError(422, "VALIDATION_ERROR", "Shares must sum to 100")
        for i in items:
            conn.execute(
                "UPDATE project_researchers SET share_pct=? WHERE project_id=? AND researcher_id=?",
                (round(i.share_pct, 2), project_id, i.researcher_id),
            )
        notify_many(
            conn, [r["researcher_id"] for r in rrows if r["researcher_id"] != user.id], "shares_changed",
            "Researcher shares updated", "The lead updated reward shares for: " + title, "/projects/" + project_id,
        )
    rrows = researchers_of(conn, project_id)
    return [{"researcher_id": r["researcher_id"], "name": r["name"], "role": r["role"], "share_pct": round(float(r["share_pct"]), 2)} for r in rrows]


def counts(conn, user: CurrentUser, project_id: str) -> dict:
    role = require_project_access(conn, project_id, user)
    def c(sql, args):
        return int(conn.execute(sql, args).fetchone()[0])
    pending_sub = "SELECT COUNT(*) FROM work_submissions WHERE project_id=? AND status='pending'"
    return {
        "pending_approvals": c(pending_sub, (project_id,)) if role != "student" else 0,
        "my_pending_submissions": c(pending_sub + " AND student_id=?", (project_id, user.id)) if role == "student" else 0,
        "pending_student_requests": c("SELECT COUNT(*) FROM student_requests WHERE project_id=? AND status='pending'", (project_id,))
        if role in RESEARCHER_ROLES
        else 0,
    }
