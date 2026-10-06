import json
from urllib.parse import urlparse

from app.core.db import now, transaction
from app.core.errors import AppError
from app.core.notify import notify
from app.core.skills import SKILL_IDS

LINK_KEYS = ("github", "linkedin", "website", "scholar")
MAX_DETAILS_BYTES = 20 * 1024


def _loads(raw, default):
    try:
        v = json.loads(raw) if raw else default
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _user(conn, user_id: str):
    r = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if r is None:
        raise AppError(404, "NOT_FOUND", "User not found")
    return r


def _rating_and_done(conn, u):
    if u["role"] == "researcher":
        r = conn.execute("SELECT rating FROM researchers WHERE user_id=?", (u["id"],)).fetchone()
        done = conn.execute(
            "SELECT COUNT(*) AS c FROM project_researchers pr JOIN projects p ON p.id = pr.project_id "
            "WHERE pr.researcher_id=? AND p.status='completed'", (u["id"],),
        ).fetchone()["c"]
        return (r["rating"] if r else None), done
    if u["role"] == "student":
        s = conn.execute("SELECT temp_rating, final_rating, projects_done FROM students WHERE user_id=?", (u["id"],)).fetchone()
        if s is None:
            return None, 0
        return (s["temp_rating"] if s["projects_done"] == 0 else s["final_rating"]), s["projects_done"]
    done = conn.execute(
        "SELECT COUNT(*) AS c FROM projects p JOIN problems pr ON pr.id = p.problem_id WHERE pr.sponsor_id=? AND p.status='completed'",
        (u["id"],),
    ).fetchone()["c"]
    return None, done


def _skills(conn, u):
    if u["role"] == "researcher":
        r = conn.execute("SELECT skills FROM researchers WHERE user_id=?", (u["id"],)).fetchone()
        return _loads(r["skills"] if r else None, []), []
    if u["role"] == "student":
        s = conn.execute("SELECT skills, pending_skills FROM students WHERE user_id=?", (u["id"],)).fetchone()
        if s is None:
            return [], []
        return _loads(s["skills"], []), _loads(s["pending_skills"], [])
    return [], []


def _works(conn, u, is_me: bool) -> list[dict]:
    uid = u["id"]
    if u["role"] == "sponsor":
        rows = conn.execute(
            "SELECT p.id, pr.title, p.status, p.created_at AS started_at, p.completed_at, 'sponsor' AS my_role, NULL AS skill "
            "FROM projects p JOIN problems pr ON pr.id = p.problem_id WHERE pr.sponsor_id=?", (uid,)).fetchall()
    elif u["role"] == "researcher":
        rows = conn.execute(
            "SELECT p.id, pr.title, p.status, COALESCE(x.joined_at, p.created_at) AS started_at, p.completed_at, x.role AS my_role, NULL AS skill "
            "FROM project_researchers x JOIN projects p ON p.id = x.project_id JOIN problems pr ON pr.id = p.problem_id "
            "WHERE x.researcher_id=?", (uid,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT p.id, pr.title, p.status, COALESCE(m.joined_at, p.created_at) AS started_at, p.completed_at, 'student' AS my_role, m.skill AS skill "
            "FROM project_members m JOIN projects p ON p.id = m.project_id JOIN problems pr ON pr.id = p.problem_id "
            "WHERE m.student_id=?", (uid,)).fetchall()
    out = []
    for r in rows:
        cnt = conn.execute("SELECT COUNT(*) AS c FROM submission_files WHERE project_id=? AND is_public=1", (r["id"],)).fetchone()["c"]
        if cnt == 0 and not is_me:
            continue
        out.append({
            "project_id": r["id"], "title": r["title"], "my_role": r["my_role"], "skill": r["skill"], "status": r["status"],
            "public_file_count": cnt, "started_at": r["started_at"], "completed_at": r["completed_at"],
        })
    out.sort(key=lambda w: w["started_at"] or "", reverse=True)
    return out


def get_profile(conn, target_id: str, viewer) -> dict:
    u = _user(conn, target_id)
    is_me = viewer.id == u["id"]
    if u["is_blacklisted"] and not is_me:
        raise AppError(404, "NOT_FOUND", "User not found")
    p = conn.execute("SELECT * FROM profiles WHERE user_id=?", (target_id,)).fetchone()
    skills, pending = _skills(conn, u)
    rating, done = _rating_and_done(conn, u)
    likes = conn.execute("SELECT COUNT(*) AS c FROM profile_likes WHERE user_id=?", (target_id,)).fetchone()["c"]
    liked = conn.execute("SELECT 1 FROM profile_likes WHERE liker_id=? AND user_id=?", (viewer.id, target_id)).fetchone() is not None
    return {
        "user": {"id": u["id"], "role": u["role"], "name": u["name"]},
        "headline": p["headline"] if p else "",
        "about": p["about"] if p else "",
        "location": p["location"] if p else "",
        "links": _loads(p["links"], {}) if p else {},
        "details": _loads(p["details"], {}) if p else {},
        "skills": skills,
        "pending_skills": pending if is_me else [],
        "rating": rating,
        "projects_done": done,
        "likes_count": likes,
        "liked_by_me": liked,
        "is_me": is_me,
        "member_since": u["created_at"],
        "works": _works(conn, u, is_me),
    }


def _valid_url(v: str) -> bool:
    try:
        p = urlparse(v)
    except ValueError:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc) and len(v) <= 500


def update_profile(conn, user, body) -> dict:
    sent = body.model_fields_set
    u = _user(conn, user.id)
    fields: dict = {}
    if "name" in sent and body.name is not None:
        name = body.name.strip()
        if not (2 <= len(name) <= 80):
            raise AppError(422, "VALIDATION_ERROR", "Name must be 2-80 characters")
        fields["name"] = name
    if "headline" in sent and body.headline is not None:
        if len(body.headline) > 120:
            raise AppError(422, "VALIDATION_ERROR", "Headline must be at most 120 characters")
        fields["headline"] = body.headline.strip()
    if "about" in sent and body.about is not None:
        if len(body.about) > 2000:
            raise AppError(422, "VALIDATION_ERROR", "About must be at most 2000 characters")
        fields["about"] = body.about.strip()
    if "location" in sent and body.location is not None:
        if len(body.location) > 200:
            raise AppError(422, "VALIDATION_ERROR", "Location must be at most 200 characters")
        fields["location"] = body.location.strip()
    if "links" in sent and body.links is not None:
        links = {}
        for k, v in body.links.items():
            if k not in LINK_KEYS:
                raise AppError(422, "VALIDATION_ERROR", f"Unknown link: {k}")
            v = (v or "").strip()
            if not v:
                continue
            if not _valid_url(v):
                raise AppError(422, "VALIDATION_ERROR", f"Link '{k}' must be an http(s) URL")
            links[k] = v
        fields["links"] = json.dumps(links)
    if "details" in sent and body.details is not None:
        raw = json.dumps(body.details, ensure_ascii=False)
        if len(raw.encode("utf-8")) > MAX_DETAILS_BYTES:
            raise AppError(422, "VALIDATION_ERROR", "Details must be at most 20KB")
        fields["details"] = raw

    add = list(dict.fromkeys(body.add_skills or []))
    rem = list(dict.fromkeys(body.remove_skills or []))
    for s in add:
        if s not in SKILL_IDS:
            raise AppError(422, "VALIDATION_ERROR", f"Unknown skill: {s}")

    skill_update = None  # (table, column, value)
    if u["role"] == "student" and (add or rem):
        s = conn.execute("SELECT skills, pending_skills FROM students WHERE user_id=?", (u["id"],)).fetchone()
        skills, pending = _loads(s["skills"], []), _loads(s["pending_skills"], [])
        skills = [x for x in skills if x not in rem]
        pending = [x for x in pending if x not in rem]
        for sk in add:
            if sk not in skills and sk not in pending:
                pending.append(sk)
        skill_update = ("students", json.dumps(skills), json.dumps(pending))
    elif u["role"] == "researcher" and (add or rem):
        r = conn.execute("SELECT skills FROM researchers WHERE user_id=?", (u["id"],)).fetchone()
        skills = [x for x in _loads(r["skills"], []) if x not in rem]
        for sk in add:
            if sk not in skills:
                skills.append(sk)
        if len(skills) < 1:
            raise AppError(422, "VALIDATION_ERROR", "A researcher must keep at least one skill")
        skill_update = ("researchers", json.dumps(skills), None)

    with transaction(conn):
        if "name" in fields:
            conn.execute("UPDATE users SET name=? WHERE id=?", (fields["name"], u["id"]))
        prof_fields = {k: v for k, v in fields.items() if k != "name"}
        if prof_fields or "name" in fields:
            conn.execute("INSERT OR IGNORE INTO profiles(user_id, updated_at) VALUES(?,?)", (u["id"], now()))
            sets = ", ".join(f"{k}=?" for k in prof_fields)
            conn.execute(f"UPDATE profiles SET {sets + ', ' if sets else ''}updated_at=? WHERE user_id=?", [*prof_fields.values(), now(), u["id"]])
        if skill_update:
            if skill_update[0] == "students":
                conn.execute("UPDATE students SET skills=?, pending_skills=? WHERE user_id=?", (skill_update[1], skill_update[2], u["id"]))
            else:
                conn.execute("UPDATE researchers SET skills=? WHERE user_id=?", (skill_update[1], u["id"]))

    return get_profile(conn, u["id"], user)


def _like_state(conn, target_id: str, viewer_id: str) -> dict:
    c = conn.execute("SELECT COUNT(*) AS c FROM profile_likes WHERE user_id=?", (target_id,)).fetchone()["c"]
    liked = conn.execute("SELECT 1 FROM profile_likes WHERE liker_id=? AND user_id=?", (viewer_id, target_id)).fetchone() is not None
    return {"likes_count": c, "liked_by_me": liked}


def like(conn, target_id: str, user) -> dict:
    t = _user(conn, target_id)
    if t["id"] == user.id:
        raise AppError(400, "BAD_STATE", "You cannot like your own profile")
    with transaction(conn):
        cur = conn.execute("INSERT OR IGNORE INTO profile_likes(liker_id, user_id, created_at) VALUES(?,?,?)", (user.id, t["id"], now()))
        if cur.rowcount == 1:
            notify(conn, t["id"], "profile_like", "Someone liked your profile", f"{user.name} liked your profile.", f"/profile/{user.id}")
    return _like_state(conn, t["id"], user.id)


def unlike(conn, target_id: str, user) -> dict:
    t = _user(conn, target_id)
    if t["id"] == user.id:
        raise AppError(400, "BAD_STATE", "You cannot like your own profile")
    with transaction(conn):
        conn.execute("DELETE FROM profile_likes WHERE liker_id=? AND user_id=?", (user.id, t["id"]))
    return _like_state(conn, t["id"], user.id)
