import json
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "activity_test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["LLM_MOCK"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import get_conn, init_db, new_id  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def mk_user(conn, role, name):
    uid = new_id()
    conn.execute(
        "INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
        (uid, role, name, f"{uid}@t.com", "x", "2026-01-01T00:00:00+00:00"),
    )
    return uid, {"Authorization": "Bearer " + create_access_token(uid, role)}


def test_activity_filters_order_limit_and_access():
    conn = get_conn()
    sp, sph = mk_user(conn, "sponsor", "Sam")
    lead, leadh = mk_user(conn, "researcher", "Lena")
    st, sth = mk_user(conn, "student", "Stu")
    st2, st2h = mk_user(conn, "student", "Other")
    out, outh = mk_user(conn, "student", "Outsider")
    pid, prj = new_id(), new_id()
    conn.execute(
        "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, required_skills, status, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (pid, sp, "P", "D", 100, 30, "[]", "matched", "2026-01-01T00:00:00+00:00"),
    )
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)", (prj, pid, lead, "active", "2026-01-01T00:00:00+00:00"))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, joined_at) VALUES(?,?,?,?)", (prj, lead, "lead", "2026-01-01T00:00:00+00:00"))
    for s in (st, st2):
        conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) VALUES(?,?,?,?,?)", (prj, s, "python", "active", "2026-01-01T00:00:00+00:00"))
    rows = [
        ("project_created", lead, {}, "2026-01-02T00:00:00+00:00"),
        ("submission_created", st, {"student_id": st}, "2026-01-03T00:00:00+00:00"),
        ("submission_approved", lead, {"student_id": st}, "2026-01-04T00:00:00+00:00"),
        ("submission_created", st2, {"student_id": st2}, "2026-01-05T00:00:00+00:00"),
        ("project_completed", None, {}, "2026-01-06T00:00:00+00:00"),
    ]
    for t, actor, meta, ts in rows:
        conn.execute(
            "INSERT INTO project_events(id, project_id, actor_id, type, message, ref_id, meta, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (new_id(), prj, actor, t, t, None, json.dumps(meta), ts),
        )
    conn.close()

    r = client.get(f"/projects/{prj}/activity", headers=sph)
    assert r.status_code == 200
    items = r.json()
    assert [i["type"] for i in items][0] == "project_completed" and len(items) == 5
    assert items[0]["actor"] is None and items[1]["actor"]["name"] == "Stu" and items[1]["meta"] == {"student_id": st2}
    mine = client.get(f"/projects/{prj}/activity?user_id={st}", headers=st2h).json()
    assert [i["type"] for i in mine] == ["submission_approved", "submission_created"]  # actor OR meta.student_id
    assert len(client.get(f"/projects/{prj}/activity?limit=2", headers=leadh).json()) == 2
    assert len(client.get(f"/projects/{prj}/activity?limit=9999", headers=leadh).json()) == 5
    assert client.get(f"/projects/{prj}/activity", headers=outh).status_code == 403
    assert client.get(f"/projects/{new_id()}/activity", headers=sph).status_code == 404
