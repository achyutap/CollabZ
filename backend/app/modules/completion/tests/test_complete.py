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

def _sub(conn, pid, sid, status, score, originality="original", files=0):
    subid = new_id()
    conn.execute(
        "INSERT INTO work_submissions(id, project_id, student_id, commit_msg, status, ai_quality_score, created_at, "
        "originality) VALUES(?,?,?,?,?,?,?,?)", (subid, pid, sid, "did something useful", status, score, now(), originality))
    for i in range(files):
        conn.execute(
            "INSERT INTO submission_files(id, submission_id, project_id, author_id, path, name, size, content_type, "
            "is_text, storage_path, version, originality, is_public, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0,?)",
            (new_id(), subid, pid, sid, f"f{i}.txt", f"f{i}.txt", 1, "text/plain", 1, "x", 1, originality, now()))


@pytest.fixture()
def env():
    conn = _wipe()
    d = dict(conn=conn, c=TestClient(app))
    d["sponsor"], d["lead"], d["co"] = _user(conn, "sponsor", "Sp"), _user(conn, "researcher", "Lead"), _user(conn, "researcher", "Co")
    for k, n in (("a", "Alice"), ("b", "Bob"), ("r", "Remo"), ("x", "Xena")):
        d[k] = _user(conn, "student", n)
    d["pid"], d["prid"] = _make_project(conn, d["sponsor"], d["lead"], [d["co"]], [d["a"], d["b"], d["r"], d["x"]])
    conn.execute("INSERT INTO wallets VALUES(?,?)", (d["sponsor"], 400000.0))
    conn.execute("INSERT INTO ledger_entries(id, user_id, problem_id, project_id, amount, type, created_at) "
                 "VALUES(?,?,?,?,?,?,?)", (new_id(), d["sponsor"], d["prid"], None, -100000.0, "escrow", now()))
    yield d
    conn.close()


def _ledger_sum(conn, types):
    q = ",".join("?" * len(types))
    return conn.execute(f"SELECT COALESCE(SUM(amount),0) FROM ledger_entries WHERE type IN ({q})", types).fetchone()[0]


def test_full_flow(env):
    conn, c, pid = env["conn"], env["c"], env["pid"]
    a, b, r, x = env["a"], env["b"], env["r"], env["x"]
    conn.execute("UPDATE project_members SET status='removed', removed_at=? WHERE student_id=?", (now(), r))
    conn.execute("UPDATE project_members SET status='blacklisted' WHERE student_id=?", (x,))
    for _ in range(4):
        _sub(conn, pid, a, "approved", 0.8, files=2)
    _sub(conn, pid, a, "rejected", 0.1)
    _sub(conn, pid, a, "approved", 1.0, originality="copied", files=3)   # copied -> ignored
    _sub(conn, pid, b, "approved", 0.9, files=1)
    _sub(conn, pid, r, "approved", 0.9)
    _sub(conn, pid, x, "approved", 0.9)
    _sub(conn, pid, x, "pending", 0.9)                                  # blacklisted pending must not block
    conn.execute("UPDATE students SET temp_rating=3.5 WHERE user_id=?", (a,))

    for uid, role in ((env["co"], "researcher"), (env["sponsor"], "sponsor"), (a, "student")):
        assert c.post(f"/projects/{pid}/complete", headers=_h(uid, role)).status_code == 403
    res = c.post(f"/projects/{pid}/complete", headers=_h(env["lead"], "researcher"))
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["budget"], body["student_pool"], body["researcher_pool"], body["project_fund"]) == (
        100000, 30000, 60000, 10000)
    sts = {s["student_id"]: s for s in body["students"]}
    assert set(sts) == {a, b, r}                                         # blacklisted excluded
    assert sts[r]["status"] == "removed" and sts[r]["amount"] > 0
    assert sts[a]["submitted"] == 5 and sts[a]["approved"] == 4 and sts[a]["files_count"] == 8
    assert sts[b]["amount"] == sts[r]["amount"]
    assert round(sum(s["amount"] for s in sts.values()), 2) == 30000
    assert sts[a]["old_rating"] == 3.5
    rs = {x_["researcher_id"]: x_ for x_ in body["researchers"]}
    assert rs[env["lead"]]["amount"] == 30000 and rs[env["co"]]["amount"] == 30000
    assert rs[env["lead"]]["role"] == "lead" and rs[env["lead"]]["share_pct"] == 50
    assert round(sum(t["amount"] for t in body["transactions"]), 2) == 100000
    kinds = {t["kind"] for t in body["transactions"]}
    assert kinds == {"student_reward", "researcher_share", "project_fund"}
    assert all(t["user_id"] != x for t in body["transactions"])
    assert body["completed_at"] and body["refunded"] == 0
    assert round(_ledger_sum(conn, ["payout", "refund", "project_fund"]), 2) == 100000
    assert conn.execute("SELECT type FROM ledger_entries WHERE type='project_fund'").fetchone() is not None
    assert conn.execute("SELECT temp_rating FROM students WHERE user_id=?", (a,)).fetchone()[0] is None
    assert conn.execute("SELECT status FROM problems WHERE id=?", (env["prid"],)).fetchone()[0] == "completed"
    assert conn.execute("SELECT COUNT(*) FROM project_events WHERE type='project_completed'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notifications WHERE type='project_completed'").fetchone()[0] == 6
    assert conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='project_completed'", (x,)).fetchone()[0] == 0

    again = c.post(f"/projects/{pid}/complete", headers=_h(env["lead"], "researcher"))
    assert again.status_code == 409 and again.json()["code"] == "CONFLICT"

    for uid, role in ((env["sponsor"], "sponsor"), (env["co"], "researcher"), (r, "student"), (a, "student")):
        g = c.get(f"/projects/{pid}/payout", headers=_h(uid, role))
        assert g.status_code == 200, (role, g.text)
        assert round(sum(t["amount"] for t in g.json()["transactions"]), 2) == 100000
        assert {s["student_id"] for s in g.json()["students"]} == {a, b, r}
    assert c.get(f"/projects/{pid}/payout", headers=_h(x, "student")).status_code == 403


def test_pending_blocks_and_payout_before_complete(env):
    conn, c, pid = env["conn"], env["c"], env["pid"]
    _sub(conn, pid, env["a"], "pending", 0.5)
    _sub(conn, pid, env["b"], "pending", 0.5)
    r = c.post(f"/projects/{pid}/complete", headers=_h(env["lead"], "researcher"))
    assert r.status_code == 400 and r.json()["code"] == "BAD_STATE" and "2 submissions still pending" in r.json()["detail"]
    assert c.get(f"/projects/{pid}/payout", headers=_h(env["lead"], "researcher")).status_code == 400


def test_weighted_researcher_shares_and_zero_approval_refund(env):
    conn, c, pid = env["conn"], env["c"], env["pid"]
    conn.execute("UPDATE project_researchers SET share_pct=70 WHERE role='lead'")
    conn.execute("UPDATE project_researchers SET share_pct=30 WHERE role='researcher'")
    _sub(conn, pid, env["a"], "rejected", 0.3)
    _sub(conn, pid, env["b"], "approved", 0.9, originality="copied")
    res = c.post(f"/projects/{pid}/complete", headers=_h(env["lead"], "researcher"))
    assert res.status_code == 200, res.text
    body = res.json()
    rs = {x_["researcher_id"]: x_["amount"] for x_ in body["researchers"]}
    assert rs[env["lead"]] == 42000 and rs[env["co"]] == 18000
    assert body["refunded"] == 30000 and all(s["amount"] == 0 and s["project_score"] == 1.0 for s in body["students"])
    assert conn.execute("SELECT COUNT(*) FROM rewards").fetchone()[0] == 0
    assert conn.execute("SELECT balance FROM wallets WHERE user_id=?", (env["sponsor"],)).fetchone()[0] == 430000
    assert "refund" in {t["kind"] for t in body["transactions"]}
    assert round(sum(t["amount"] for t in body["transactions"]), 2) == 100000
    g = c.get(f"/projects/{pid}/payout", headers=_h(env["sponsor"], "sponsor")).json()
    assert g["refunded"] == 30000
