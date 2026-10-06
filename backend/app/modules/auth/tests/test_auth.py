import os
import tempfile

os.environ["LLM_MOCK"] = "true"
os.environ["AUTO_SEED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.core.db import init_db


@pytest.fixture(scope="module")
def client():
    d = tempfile.mkdtemp()
    os.environ["DB_PATH"] = os.path.join(d, "auth_test.db")
    init_db()
    from app.main import app

    return TestClient(app)


def reg(client, email, role, **kw):
    body = {"email": email, "password": "demo1234", "name": "Test " + role, "role": role}
    body.update(kw)
    return client.post("/auth/register", json=body)


def test_register_each_role_and_me(client):
    r = reg(client, "s1@t.com", "sponsor")
    assert r.status_code == 200
    j = r.json()
    assert j["token_type"] == "bearer" and j["user"]["role"] == "sponsor" and j["user"]["has_taken_quiz"] is True
    h = {"Authorization": "Bearer " + j["access_token"]}
    assert client.get("/auth/me", headers=h).json()["email"] == "s1@t.com"

    r = reg(client, "r1@t.com", "researcher", skills=["python", "bogus"], bio="I research things")
    assert r.status_code == 200
    rid = r.json()["user"]["id"]
    out = client.get(f"/researchers/{rid}", headers=h).json()
    assert out["skills"] == ["python"] and out["rating"] == 3.0 and out["availability"] == 1.0

    r = reg(client, "st1@t.com", "student")
    assert r.status_code == 200 and r.json()["user"]["has_taken_quiz"] is False
    sid = r.json()["user"]["id"]
    s = client.get(f"/students/{sid}", headers=h).json()
    assert s["rating"] is None and s["rating_type"] is None and s["projects_done"] == 0 and s["skills"] == []
    assert client.get(f"/students/{rid}", headers=h).status_code == 404
    assert client.get(f"/researchers/{sid}", headers=h).status_code == 404


def test_duplicate_email_409(client):
    assert reg(client, "dup@t.com", "student").status_code == 200
    r = reg(client, "DUP@t.com", "student")
    assert r.status_code == 409 and r.json()["code"] == "CONFLICT"


def test_login_ok_and_wrong_password(client):
    reg(client, "login@t.com", "student")
    ok = client.post("/auth/login", json={"email": "login@t.com", "password": "demo1234"})
    assert ok.status_code == 200 and "access_token" in ok.json()
    bad = client.post("/auth/login", json={"email": "login@t.com", "password": "wrongpass"})
    assert bad.status_code == 401 and bad.json() == {"detail": "Invalid email or password", "code": "UNAUTHORIZED"}
    unk = client.post("/auth/login", json={"email": "nobody@t.com", "password": "demo1234"})
    assert unk.status_code == 401 and unk.json()["detail"] == "Invalid email or password"


def test_researcher_validation(client):
    r = reg(client, "rv1@t.com", "researcher", bio="bio only")
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"
    r = reg(client, "rv2@t.com", "researcher", skills=["python"])
    assert r.status_code == 200  # bio is optional in v2
    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert client.get("/researchers/" + r.json()["user"]["id"], headers=h).json()["bio"] == ""
    r = reg(client, "rv3@t.com", "researcher", skills=["nope"], bio="x")
    assert r.status_code == 422


def test_sponsor_wallet(client):
    r = reg(client, "wallet@t.com", "sponsor").json()
    h = {"Authorization": "Bearer " + r["access_token"]}
    w = client.get("/me/wallet", headers=h).json()
    assert w["balance"] == 500000
    assert len(w["entries"]) == 1
    e = w["entries"][0]
    assert e["amount"] == 500000 and e["type"] == "seed" and e["problem_id"] is None and e["project_id"] is None
    assert set(e) == {"id", "amount", "type", "problem_id", "project_id", "created_at"}


def test_missing_token_is_401(client):
    r = client.get("/me/wallet")
    assert r.status_code == 401 and r.json()["code"] == "UNAUTHORIZED"


def test_student_register_with_skills_and_pending(client):
    r = reg(client, "ps@t.com", "student", skills=["python", "sql", "python", "bogus"])
    j = r.json()
    assert r.status_code == 200
    assert j["user"]["pending_quiz_skills"] == ["python", "sql"]
    h = {"Authorization": "Bearer " + j["access_token"]}
    me = client.get("/auth/me", headers=h).json()
    assert me["pending_quiz_skills"] == ["python", "sql"] and me["has_taken_quiz"] is False
    own = client.get("/students/" + j["user"]["id"], headers=h).json()
    assert own["skills"] == [] and own["pending_skills"] == ["python", "sql"]
    other = reg(client, "ps2@t.com", "sponsor").json()
    oh = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get("/students/" + j["user"]["id"], headers=oh).json()["pending_skills"] == []
    assert other["user"]["pending_quiz_skills"] == []


def test_profile_row_created(client):
    from app.core.db import get_conn

    uid = reg(client, "prof@t.com", "sponsor").json()["user"]["id"]
    conn = get_conn()
    try:
        assert conn.execute("SELECT COUNT(*) FROM profiles WHERE user_id=?", (uid,)).fetchone()[0] == 1
    finally:
        conn.close()


def test_blacklisted_login_and_calls_403(client):
    from app.core.db import get_conn

    j = reg(client, "bl@t.com", "student").json()
    h = {"Authorization": "Bearer " + j["access_token"]}
    conn = get_conn()
    try:
        conn.execute("UPDATE users SET is_blacklisted=1, blacklisted_at='2026-01-01T00:00:00+00:00' WHERE id=?", (j["user"]["id"],))
    finally:
        conn.close()
    r = client.post("/auth/login", json={"email": "bl@t.com", "password": "demo1234"})
    assert r.status_code == 403 and r.json()["code"] == "BLACKLISTED"
    r = client.get("/auth/me", headers=h)
    assert r.status_code == 403 and r.json()["code"] == "BLACKLISTED"
    # wrong password still looks like a normal failure
    assert client.post("/auth/login", json={"email": "bl@t.com", "password": "wrongpass"}).status_code == 401
