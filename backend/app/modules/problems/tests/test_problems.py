import json
import os
import tempfile

_PATH = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["DB_PATH"] = _PATH
os.environ["LLM_MOCK"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_conn, init_db, new_id, now
from app.core.security import create_access_token
from app.main import app

init_db()
client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def _db():
    os.environ["DB_PATH"] = _PATH
    os.environ["LLM_MOCK"] = "true"
    init_db()
    yield


def token(uid, role):
    try:
        return create_access_token(uid, role)
    except TypeError:
        return create_access_token({"sub": uid, "role": role})


def H(u):
    return {"Authorization": "Bearer " + token(u["id"], u["role"])}


def run(sql, args=()):
    conn = get_conn()
    conn.execute(sql, args)
    conn.close()


def q(sql, args=()):
    conn = get_conn()
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return rows


def _user(role, name):
    uid = new_id()
    run("INSERT INTO users(id,role,name,email,password_hash,created_at) VALUES(?,?,?,?,?,?)", (uid, role, name, uid + "@t.com", "x", now()))
    return {"id": uid, "role": role, "name": name}


def mk_sponsor(balance=500000.0):
    u = _user("sponsor", "Sponsor")
    run("INSERT INTO wallets(user_id,balance) VALUES(?,?)", (u["id"], balance))
    return u


def mk_researcher(skills=("python",), rating=4.0, availability=1.0, name="Researcher"):
    u = _user("researcher", name)
    run("INSERT INTO researchers(user_id,skills,rating,bio,availability) VALUES(?,?,?,?,?)", (u["id"], json.dumps(list(skills)), rating, "bio", availability))
    return u


def mk_student(skills=("python",), temp=3.0, final=None, done=0, last_active=None, name="Student"):
    u = _user("student", name)
    run(
        "INSERT INTO students(user_id,skills,temp_rating,final_rating,projects_done,last_active_at) VALUES(?,?,?,?,?,?)",
        (u["id"], json.dumps(list(skills)), temp, final, done, last_active or now()),
    )
    return u


def mk_problem(sponsor, budget=1000.0, pct=40, skills=("python", "sql"), status="open", rpct=None, ppct=0):
    pid = new_id()
    rpct = 100 - pct - ppct if rpct is None else rpct
    run(
        "INSERT INTO problems(id,sponsor_id,title,description,budget,student_pct,researcher_pct,project_pct,required_skills,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (pid, sponsor["id"], "Test problem", "d" * 40, budget, pct, rpct, ppct, json.dumps(list(skills)), status, now()),
    )
    return pid


def mk_project(problem_id, researcher):
    prj = new_id()
    run("INSERT INTO projects(id,problem_id,researcher_id,status,created_at) VALUES(?,?,?,?,?)", (prj, problem_id, researcher["id"], "active", now()))
    run("INSERT INTO project_researchers(project_id,researcher_id,role,share_pct,joined_at) VALUES(?,?,?,NULL,?)", (prj, researcher["id"], "lead", now()))
    run("UPDATE problems SET status='matched' WHERE id=?", (problem_id,))
    return prj


def add_researcher(prj, r):
    run("INSERT INTO project_researchers(project_id,researcher_id,role,share_pct,joined_at) VALUES(?,?,?,NULL,?)", (prj, r["id"], "researcher", now()))


def add_member(prj, st, skill, status="active"):
    run("INSERT INTO project_members(project_id,student_id,skill,status,joined_at) VALUES(?,?,?,?,?)", (prj, st["id"], skill, status, now()))

from app.core.skills import SKILL_IDS
from app.modules.problems.service import extract_skills, keyword_skills

BODY = {"title": "Sensor dashboard", "description": "Build a python and sql data analysis pipeline for IoT sensors.", "budget": 1000, "student_pct": 40}


def test_insufficient_funds():
    s = mk_sponsor(100)
    r = client.post("/problems", json=BODY, headers=H(s))
    assert r.status_code == 400 and r.json()["code"] == "INSUFFICIENT_FUNDS"
    assert q("SELECT COUNT(*) c FROM problems WHERE sponsor_id=?", (s["id"],))[0]["c"] == 0


def test_escrow_and_wallet_debit():
    s = mk_sponsor(5000)
    r = client.post("/problems", json=BODY, headers=H(s))
    assert r.status_code == 200
    p = r.json()
    assert p["status"] == "open" and p["sponsor_name"] == "Sponsor" and p["budget"] == 1000
    assert q("SELECT balance FROM wallets WHERE user_id=?", (s["id"],))[0]["balance"] == 4000
    led = q("SELECT amount,type,problem_id FROM ledger_entries WHERE user_id=?", (s["id"],))[0]
    assert led["amount"] == -1000 and led["type"] == "escrow" and led["problem_id"] == p["id"]


def test_pct_defaults_and_sum_rule():
    s = mk_sponsor()
    p = client.post("/problems", json=BODY, headers=H(s)).json()
    assert (p["student_pct"], p["researcher_pct"], p["project_pct"]) == (40, 60, 0)
    p2 = client.post("/problems", json={**BODY, "project_pct": 10}, headers=H(s)).json()
    assert (p2["researcher_pct"], p2["project_pct"]) == (50, 10)
    p3 = client.post("/problems", json={**BODY, "researcher_pct": 30, "project_pct": 30}, headers=H(s))
    assert p3.status_code == 200 and p3.json()["researcher_pct"] == 30
    bad = client.post("/problems", json={**BODY, "researcher_pct": 50, "project_pct": 20}, headers=H(s))
    assert bad.status_code == 422
    assert client.post("/problems", json={**BODY, "student_pct": 80, "project_pct": 30}, headers=H(s)).status_code == 422
    assert q("SELECT COUNT(*) c FROM problems WHERE sponsor_id=?", (s["id"],))[0]["c"] == 3


def test_llm_fallback_keywords():
    sk = extract_skills("Sensor", "python python sql")
    assert sk and all(x in SKILL_IDS for x in sk) and len(sk) <= 5
    assert keyword_skills("zzz", "qqq") == ["data_analysis"]


def test_taxonomy_filtering(monkeypatch):
    from app.modules.problems import service

    monkeypatch.setattr(service, "complete_json", lambda s, u: {"required_skills": ["python", "bogus", "python", "sql"]})
    assert extract_skills("t", "d") == ["python", "sql"]


def test_access_control_and_patch():
    s, s2, r, st = mk_sponsor(), mk_sponsor(), mk_researcher(), mk_student()
    pid = mk_problem(s)
    assert client.get("/problems", headers=H(st)).status_code == 403
    assert client.get(f"/problems/{pid}", headers=H(s2)).status_code == 403
    assert client.get(f"/problems/{pid}", headers=H(r)).status_code == 403
    assert client.get(f"/problems/{new_id()}", headers=H(s)).status_code == 404
    assert [p["id"] for p in client.get("/problems", headers=H(s)).json()] == [pid]
    assert client.patch(f"/problems/{pid}/skills", json={"required_skills": ["nope"]}, headers=H(s)).status_code == 422
    ok = client.patch(f"/problems/{pid}/skills", json={"required_skills": ["ml", "sql"]}, headers=H(s))
    assert ok.status_code == 200 and ok.json()["required_skills"] == ["ml", "sql"]


def test_project_researcher_can_view_problem():
    s, lead, co = mk_sponsor(), mk_researcher(), mk_researcher()
    pid = mk_problem(s)
    prj = mk_project(pid, lead)
    assert client.get(f"/problems/{pid}", headers=H(lead)).status_code == 200
    assert client.get(f"/problems/{pid}", headers=H(co)).status_code == 403
    add_researcher(prj, co)
    assert client.get(f"/problems/{pid}", headers=H(co)).status_code == 200


def test_patch_after_matched():
    s, r = mk_sponsor(), mk_researcher()
    pid = mk_problem(s)
    mk_project(pid, r)
    resp = client.patch(f"/problems/{pid}/skills", json={"required_skills": ["ml"]}, headers=H(s))
    assert resp.status_code == 400 and resp.json()["code"] == "BAD_STATE"
