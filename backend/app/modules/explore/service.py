import json

from app.core.access import project_role
from app.core.errors import AppError

ROLES = {"sponsor", "researcher", "student"}


def _loads(raw, default):
    try:
        v = json.loads(raw) if raw else default
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def people(conn, q: str | None, role: str | None) -> list[dict]:
    if role and role not in ROLES:
        raise AppError(422, "VALIDATION_ERROR", "Invalid role")
    sql = (
        "SELECT u.id, u.name, u.role, COALESCE(pf.headline, '') AS headline, "
        "r.skills AS r_skills, r.rating AS r_rating, s.skills AS s_skills, s.temp_rating, s.final_rating, s.projects_done, "
        "(SELECT COUNT(*) FROM profile_likes l WHERE l.user_id = u.id) AS likes_count "
        "FROM users u LEFT JOIN profiles pf ON pf.user_id = u.id "
        "LEFT JOIN researchers r ON r.user_id = u.id LEFT JOIN students s ON s.user_id = u.id "
        "WHERE u.is_blacklisted = 0"
    )
    params: list = []
    if role:
        sql += " AND u.role = ?"
        params.append(role)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        sql += " AND (LOWER(u.name) LIKE ? OR LOWER(COALESCE(pf.headline, '')) LIKE ?)"
        params += [like, like]
    sql += " ORDER BY likes_count DESC, u.name ASC LIMIT 50"
    out = []
    for r in conn.execute(sql, params).fetchall():
        if r["role"] == "researcher":
            skills, rating = _loads(r["r_skills"], []), r["r_rating"]
        elif r["role"] == "student":
            skills = _loads(r["s_skills"], [])
            rating = r["temp_rating"] if r["projects_done"] == 0 else r["final_rating"]
        else:
            skills, rating = [], None
        out.append({"id": r["id"], "name": r["name"], "role": r["role"], "headline": r["headline"], "skills": skills, "rating": rating, "likes_count": r["likes_count"]})
    return out


def _public_projects(conn):
    return conn.execute(
        "SELECT p.id, p.status, pr.title, pr.description, pr.required_skills, MAX(f.created_at) AS updated_at, COUNT(f.id) AS public_file_count "
        "FROM projects p JOIN problems pr ON pr.id = p.problem_id JOIN submission_files f ON f.project_id = p.id AND f.is_public = 1 "
        "GROUP BY p.id ORDER BY updated_at DESC"
    ).fetchall()


def projects(conn, q: str | None, skill: str | None) -> list[dict]:
    out = []
    ql = q.strip().lower() if q and q.strip() else None
    for r in _public_projects(conn):
        skills = _loads(r["required_skills"], [])
        summary = (r["description"] or "")[:200]
        if ql and ql not in r["title"].lower() and ql not in summary.lower():
            continue
        if skill and skill not in skills:
            continue
        researchers = conn.execute(
            "SELECT u.id, u.name FROM project_researchers x JOIN users u ON u.id = x.researcher_id WHERE x.project_id=? "
            "ORDER BY CASE x.role WHEN 'lead' THEN 0 ELSE 1 END, x.joined_at", (r["id"],)).fetchall()
        members = conn.execute(
            "SELECT u.id, u.name FROM project_members m JOIN users u ON u.id = m.student_id WHERE m.project_id=? AND m.status='active' ORDER BY m.joined_at, u.name",
            (r["id"],)).fetchall()
        out.append({
            "project_id": r["id"], "title": r["title"], "summary": summary, "required_skills": skills, "status": r["status"],
            "public_file_count": r["public_file_count"],
            "researchers": [{"id": x["id"], "name": x["name"]} for x in researchers],
            "members": [{"id": x["id"], "name": x["name"]} for x in members],
            "updated_at": r["updated_at"],
        })
    return out


def _file_out(r) -> dict:
    return {
        "id": r["id"], "submission_id": r["submission_id"], "project_id": r["project_id"], "path": r["path"], "name": r["name"],
        "size": r["size"], "content_type": r["content_type"], "is_text": bool(r["is_text"]), "version": r["version"],
        "originality": r["originality"], "is_public": bool(r["is_public"]), "author_id": r["author_id"],
        "author_name": r["author_name"], "status": r["sub_status"], "created_at": r["created_at"],
    }


def project_detail(conn, project_id: str, user) -> dict:
    p = conn.execute(
        "SELECT p.id, p.status, p.created_at, p.completed_at, pr.title, pr.description, pr.required_skills, su.name AS sponsor_name "
        "FROM projects p JOIN problems pr ON pr.id = p.problem_id JOIN users su ON su.id = pr.sponsor_id WHERE p.id=?",
        (project_id,),
    ).fetchone()
    if p is None:
        raise AppError(404, "NOT_FOUND", "Project not found")
    rows = conn.execute(
        "SELECT f.*, u.name AS author_name, s.status AS sub_status FROM submission_files f "
        "JOIN users u ON u.id = f.author_id JOIN work_submissions s ON s.id = f.submission_id "
        "WHERE f.project_id=? AND f.is_public=1 ORDER BY f.path ASC, f.version DESC",
        (project_id,),
    ).fetchall()
    if not rows and project_role(conn, project_id, user.id) is None:
        raise AppError(404, "NOT_FOUND", "Project not found")
    seen, files = set(), []
    for r in rows:
        if r["path"] not in seen:
            seen.add(r["path"])
            files.append(_file_out(r))
    researchers = conn.execute(
        "SELECT u.id, u.name, x.role, COALESCE(pf.headline, '') AS headline FROM project_researchers x JOIN users u ON u.id = x.researcher_id "
        "LEFT JOIN profiles pf ON pf.user_id = u.id WHERE x.project_id=? ORDER BY CASE x.role WHEN 'lead' THEN 0 ELSE 1 END, x.joined_at",
        (project_id,)).fetchall()
    members = conn.execute(
        "SELECT u.id, u.name, m.skill FROM project_members m JOIN users u ON u.id = m.student_id WHERE m.project_id=? AND m.status='active' ORDER BY m.joined_at, u.name",
        (project_id,)).fetchall()
    return {
        "project_id": p["id"], "title": p["title"], "description": p["description"],
        "required_skills": _loads(p["required_skills"], []), "status": p["status"], "sponsor_name": p["sponsor_name"],
        "researchers": [{"id": x["id"], "name": x["name"], "role": x["role"], "headline": x["headline"]} for x in researchers],
        "members": [{"id": x["id"], "name": x["name"], "skill": x["skill"]} for x in members],
        "started_at": p["created_at"], "completed_at": p["completed_at"], "files": files,
    }
