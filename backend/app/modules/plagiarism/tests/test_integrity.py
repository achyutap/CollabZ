import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "acc3_v2.db")
os.environ["UPLOAD_DIR"] = os.path.join(tempfile.mkdtemp(), "uploads")
os.environ["LLM_MOCK"] = "true"

import json
import random

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.db import get_conn, init_db, new_id, now
from app.main import app

TABLES = ["notifications", "project_events", "integrity_events", "file_chunks", "submission_files",
          "project_researchers", "profile_likes", "profiles", "ledger_entries", "wallets", "chat_messages",
          "document_chunks", "documents", "quiz_attempts", "quiz_questions", "project_ratings", "rewards",
          "work_submissions", "project_members", "student_requests", "skill_needs", "projects",
          "researcher_requests", "problems", "students", "researchers", "users"]


def _words(seed, n=250):
    rng = random.Random(seed)
    return " ".join(f"term{rng.randrange(5000)}x{seed}" for _ in range(n))


def _token(uid, role):
    try:
        return security.create_access_token(uid, role)
    except TypeError:
        return security.create_access_token({"sub": uid, "role": role})


def _h(uid, role):
    return {"Authorization": f"Bearer {_token(uid, role)}"}


def _wipe():
    init_db()
    conn = get_conn()
    conn.execute("PRAGMA foreign_keys=OFF")
    for t in TABLES:
        conn.execute(f"DELETE FROM {t}")
    return conn


def _user(conn, role, name):
    uid = new_id()
    conn.execute("INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
                 (uid, role, name, f"{uid}@t.com", "x", now()))
    if role == "student":
        conn.execute("INSERT INTO students(user_id, last_active_at) VALUES(?,?)", (uid, now()))
    if role == "researcher":
        conn.execute("INSERT INTO researchers(user_id) VALUES(?)", (uid,))
    return uid


def _make_project(conn, sponsor, lead, co=(), members=(), budget=100000.0, spct=30, rpct=60, ppct=10,
                  status="active"):
    pid, prid = new_id(), new_id()
    conn.execute(
        "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, required_skills, status, "
        "created_at, researcher_pct, project_pct) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (prid, sponsor, "T", "D", budget, spct, "[]", "matched", now(), rpct, ppct))
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)",
                 (pid, prid, lead, status, now()))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, share_pct, joined_at) "
                 "VALUES(?,?,?,?,?)", (pid, lead, "lead", None, now()))
    for c in co:
        conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, share_pct, joined_at) "
                     "VALUES(?,?,?,?,?)", (pid, c, "researcher", None, now()))
    for s in members:
        conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) "
                     "VALUES(?,?,?,?,?)", (pid, s, "python", "active", now()))
    return pid, prid

@pytest.fixture()
def env():
    conn = _wipe()
    sponsor, lead, co = _user(conn, "sponsor", "Sp"), _user(conn, "researcher", "Lead"), _user(conn, "researcher", "Co")
    a, out = _user(conn, "student", "Ann"), _user(conn, "student", "Out")
    pid, _ = _make_project(conn, sponsor, lead, [co], [a])
    for act, uid in (("warned", a), ("blocked", a)):
        conn.execute("INSERT INTO integrity_events(id, user_id, project_id, submission_id, action, detail, created_at) "
                     "VALUES(?,?,?,?,?,?,?)", (new_id(), uid, pid, None, act, f"{act} detail", now()))
    yield dict(conn=conn, sponsor=sponsor, lead=lead, co=co, a=a, out=out, pid=pid, c=TestClient(app))
    conn.close()


def test_project_integrity_access(env):
    c, pid = env["c"], env["pid"]
    for uid, role in ((env["lead"], "researcher"), (env["co"], "researcher"), (env["sponsor"], "sponsor")):
        r = c.get(f"/projects/{pid}/integrity", headers=_h(uid, role))
        assert r.status_code == 200 and len(r.json()) == 2
        assert {"id", "student_id", "student_name", "action", "detail", "created_at"} <= set(r.json()[0])
        assert r.json()[0]["student_name"] == "Ann"
    assert c.get(f"/projects/{pid}/integrity", headers=_h(env["a"], "student")).status_code == 403
    assert c.get(f"/projects/{pid}/integrity", headers=_h(env["out"], "student")).status_code == 403


def test_my_integrity_and_removed_endpoints(env):
    c = env["c"]
    mine = c.get("/me/integrity", headers=_h(env["a"], "student")).json()
    assert len(mine) == 2 and set(mine[0]) == {"id", "action", "detail", "created_at"}
    assert c.get("/me/integrity", headers=_h(env["out"], "student")).json() == []
    assert c.get(f"/projects/{env['pid']}/documents", headers=_h(env["lead"], "researcher")).status_code in (404, 405)
