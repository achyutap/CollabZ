import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "assistant_test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["LLM_MOCK"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import get_conn, init_db, new_id, now  # noqa: E402
from app.core.llm import LLMUnavailable  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.assistant import service  # noqa: E402

init_db()
client = TestClient(app)


def mk_user(conn, role):
    uid = new_id()
    conn.execute(
        "INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
        (uid, role, role.title(), f"{uid}@t.com", "x", now()),
    )
    return uid, {"Authorization": "Bearer " + create_access_token(uid, role)}


@pytest.fixture()
def world():
    conn = get_conn()
    sp, sph = mk_user(conn, "sponsor")
    lead, leadh = mk_user(conn, "researcher")
    co, coh = mk_user(conn, "researcher")
    st, sth = mk_user(conn, "student")
    gone, goneh = mk_user(conn, "student")
    out, outh = mk_user(conn, "student")
    pid, prj = new_id(), new_id()
    conn.execute(
        "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, required_skills, status, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (pid, sp, "Water Monitor", "Sensors and dashboards", 1000, 30, '["iot","python"]', "matched", now()),
    )
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)", (prj, pid, lead, "active", now()))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, joined_at) VALUES(?,?,?,?)", (prj, lead, "lead", now()))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, joined_at) VALUES(?,?,?,?)", (prj, co, "researcher", now()))
    conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) VALUES(?,?,?,?,?)", (prj, st, "iot", "active", now()))
    conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) VALUES(?,?,?,?,?)", (prj, gone, "python", "removed", now()))
    conn.close()
    return {"prj": prj, "sp": sph, "lead": leadh, "co": coh, "st": sth, "gone": goneh, "out": outh, "st_id": st}


def chat(w, who, msg="hello"):
    return client.post(f"/projects/{w['prj']}/chat", json={"message": msg}, headers=w[who])


def test_access_control(world):
    for who in ("sp", "lead", "co", "st"):
        assert chat(world, who).status_code == 200
    assert chat(world, "gone").status_code == 403
    assert chat(world, "out").status_code == 403
    assert client.post(f"/projects/{new_id()}/chat", json={"message": "x"}, headers=world["sp"]).status_code == 404
    assert client.get(f"/projects/{world['prj']}/chat", headers=world["out"]).status_code == 403


def test_history_isolated_and_chronological(world):
    chat(world, "st", "first")
    chat(world, "sp", "sponsor msg")
    h = client.get(f"/projects/{world['prj']}/chat", headers=world["st"]).json()
    assert [m["role"] for m in h] == ["user", "assistant"]
    assert h[0]["content"] == "first" and set(h[0]) == {"id", "role", "content", "created_at"}
    assert all("sponsor msg" not in m["content"] for m in h)


def test_rate_limit_21st_message(world):
    for i in range(20):
        assert chat(world, "st", f"m{i}").status_code == 200
    r = chat(world, "st", "m21")
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"
    assert chat(world, "sp").status_code == 200  # other users unaffected


def test_history_window_and_role_in_prompt(world, monkeypatch):
    seen = {}

    def fake(system, user, json_mode=False, temperature=0.2, cache=True):
        seen["system"], seen["user"], seen["cache"] = system, user, cache
        return "ok"

    monkeypatch.setattr(service, "complete", fake)
    for i in range(7):
        chat(world, "lead", f"msg{i}")
    # 14 stored messages, last 10 = msg2..msg6 (user+assistant)
    chat(world, "lead", "latest")
    assert "msg1" not in seen["user"] and "msg2" in seen["user"]
    assert seen["user"].endswith("User: latest")
    assert seen["cache"] is False
    assert "The user is a researcher." in seen["system"] and "Water Monitor" in seen["system"] and "iot, python" in seen["system"]
    chat(world, "st")
    assert "The user is a student." in seen["system"]
    chat(world, "sp")
    assert "The user is a sponsor." in seen["system"]


def test_llm_failure_stores_nothing(world, monkeypatch):
    def boom(*a, **k):
        raise LLMUnavailable("down")

    monkeypatch.setattr(service, "complete", boom)
    r = chat(world, "st", "will fail")
    assert r.status_code == 503 and r.json()["code"] == "LLM_UNAVAILABLE"
    assert client.get(f"/projects/{world['prj']}/chat", headers=world["st"]).json() == []


def test_message_validation(world):
    assert chat(world, "st", "").status_code == 422
    assert chat(world, "st", "x" * 2001).status_code == 422
