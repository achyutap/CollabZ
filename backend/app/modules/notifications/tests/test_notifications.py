import os
import tempfile

os.environ["LLM_MOCK"] = "true"
os.environ["AUTO_SEED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_conn, init_db, new_id, now
from app.core.notify import notify
from app.core.security import create_access_token


@pytest.fixture(scope="module")
def env():
    d = tempfile.mkdtemp()
    os.environ["DB_PATH"] = os.path.join(d, "notif.db")
    init_db()
    from app.main import app

    conn = get_conn()

    def mk(role):
        uid = new_id()
        conn.execute(
            "INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
            (uid, role, role, uid + "@t.com", "x", now()),
        )
        return uid

    ids = {r: mk(r) for r in ("sponsor", "researcher", "student")}
    ids["researcher2"] = mk("researcher")
    ids["student2"] = mk("student")
    yield TestClient(app), conn, ids
    conn.close()


def H(uid, role):
    return {"Authorization": "Bearer " + create_access_token(uid, role)}


def test_counts_per_role(env):
    client, conn, ids = env
    sp, rs, rs2, st, st2 = ids["sponsor"], ids["researcher"], ids["researcher2"], ids["student"], ids["student2"]
    pid, prj, prj2 = new_id(), new_id(), new_id()
    for p in (pid, new_id()):
        conn.execute(
            "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, created_at) VALUES(?,?,?,?,?,?,?)",
            (p, sp, "t", "d", 100, 50, now()),
        )
        if p == pid:
            first = p
    second = conn.execute("SELECT id FROM problems WHERE id!=?", (first,)).fetchone()["id"]
    conn.execute("INSERT INTO researcher_requests(id, problem_id, researcher_id, match_score, created_at) VALUES(?,?,?,?,?)", (new_id(), first, rs, 0.5, now()))
    conn.execute("INSERT INTO researcher_requests(id, problem_id, researcher_id, match_score, status, created_at) VALUES(?,?,?,?,?,?)", (new_id(), second, rs, 0.5, "declined", now()))
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, created_at) VALUES(?,?,?,?)", (prj, first, rs, now()))
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)", (prj2, second, rs, "completed", now()))
    for p in (prj, prj2):
        conn.execute("INSERT INTO project_researchers VALUES(?,?,?,NULL,?)", (p, rs, "lead", now()))
    for p, sid, status in ((prj, st, "pending"), (prj, st, "approved"), (prj, st2, "pending"), (prj2, st, "pending")):
        conn.execute("INSERT INTO work_submissions(id, project_id, student_id, commit_msg, status, created_at) VALUES(?,?,?,?,?,?)", (new_id(), p, sid, "msg long enough", status, now()))
    conn.execute("INSERT INTO student_requests(id, project_id, student_id, skill, match_score, created_at) VALUES(?,?,?,?,?,?)", (new_id(), prj, st, "python", 0.5, now()))

    assert client.get("/me/counts", headers=H(sp, "sponsor")).json() == {"requests": 0, "approvals": 0, "notifications": 0}
    # researcher: 1 pending request; approvals = pending subs in ACTIVE project (2)
    assert client.get("/me/counts", headers=H(rs, "researcher")).json() == {"requests": 1, "approvals": 2, "notifications": 0}
    assert client.get("/me/counts", headers=H(rs2, "researcher")).json() == {"requests": 0, "approvals": 0, "notifications": 0}
    # student: 1 pending request; own pending submissions (incl. completed project row) = 2
    assert client.get("/me/counts", headers=H(st, "student")).json() == {"requests": 1, "approvals": 2, "notifications": 0}


def test_notifications_list_read_and_read_all(env):
    client, conn, ids = env
    u, other = ids["student"], ids["student2"]
    for i in range(3):
        notify(conn, u, "t", f"n{i}", "b", "/x")
    notify(conn, other, "t", "other")
    items = client.get("/notifications", headers=H(u, "student")).json()
    assert [i["title"] for i in items] == ["n2", "n1", "n0"]
    assert set(items[0]) == {"id", "type", "title", "body", "link", "is_read", "created_at"} and items[0]["is_read"] is False
    assert client.get("/me/counts", headers=H(u, "student")).json()["notifications"] == 3

    assert client.post(f"/notifications/{items[0]['id']}/read", headers=H(u, "student")).json() == {"ok": True}
    unread = client.get("/notifications?unread_only=true", headers=H(u, "student")).json()
    assert len(unread) == 2
    # cannot read someone else's notification
    oid = client.get("/notifications", headers=H(other, "student")).json()[0]["id"]
    r = client.post(f"/notifications/{oid}/read", headers=H(u, "student"))
    assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"

    assert client.post("/notifications/read-all", headers=H(u, "student")).json() == {"ok": True}
    assert client.get("/notifications?unread_only=true", headers=H(u, "student")).json() == []
    assert client.get("/me/counts", headers=H(u, "student")).json()["notifications"] == 0
    assert len(client.get("/notifications?unread_only=true", headers=H(other, "student")).json()) == 1


def test_notifications_limit_50_and_auth(env):
    client, conn, ids = env
    u = ids["researcher2"]
    for i in range(55):
        notify(conn, u, "t", f"m{i}")
    assert len(client.get("/notifications", headers=H(u, "researcher")).json()) == 50
    assert client.get("/notifications").status_code == 401
