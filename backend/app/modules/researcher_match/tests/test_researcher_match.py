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

from app.modules.researcher_match.service import score_researcher


def send(s, pid, *rs):
    r = client.post(f"/problems/{pid}/requests", json={"researcher_ids": [x["id"] for x in rs]}, headers=H(s))
    assert r.status_code == 200, r.text
    return r.json()


def test_score_example():
    assert score_researcher(["python", "sql"], ["python"], 4.0, 0.5) == 0.59
    assert score_researcher([], ["python"], 5.0, 1.0) == 0.4


def test_zero_overlap_excluded_and_sorted():
    s = mk_sponsor()
    pid = mk_problem(s, skills=("iot", "embedded_c"))
    full = mk_researcher(("iot", "embedded_c"), 3.0)
    part = mk_researcher(("iot",), 5.0)
    none = mk_researcher(("ui_design",), 5.0)
    res = client.get(f"/problems/{pid}/matches", headers=H(s)).json()
    ids = [m["researcher"]["id"] for m in res]
    assert full["id"] in ids and part["id"] in ids and none["id"] not in ids
    assert ids.index(full["id"]) < ids.index(part["id"])
    m = res[ids.index(part["id"])]
    assert m["matched_skills"] == ["iot"] and m["missing_skills"] == ["embedded_c"]


def test_matches_exclude_requested_and_project_researchers():
    s = mk_sponsor()
    pid = mk_problem(s, skills=("iot",))
    a, b, c = mk_researcher(("iot",)), mk_researcher(("iot",)), mk_researcher(("iot",))
    send(s, pid, a)
    prj = mk_project(pid, b)
    ids = [m["researcher"]["id"] for m in client.get(f"/problems/{pid}/matches", headers=H(s)).json()]
    assert a["id"] not in ids and b["id"] not in ids and c["id"] in ids


def test_duplicate_request_409_creates_nothing():
    s = mk_sponsor()
    pid = mk_problem(s)
    a, b = mk_researcher(), mk_researcher()
    send(s, pid, a)
    r = client.post(f"/problems/{pid}/requests", json={"researcher_ids": [b["id"], a["id"]]}, headers=H(s))
    assert r.status_code == 409
    assert len(client.get(f"/problems/{pid}/requests", headers=H(s)).json()) == 1
    assert client.post(f"/problems/{pid}/requests", json={"researcher_ids": [new_id()]}, headers=H(s)).status_code == 404
    assert q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND type='researcher_request'", (a["id"],))[0]["c"] == 1


def test_two_researchers_both_accept_lead_then_co():
    s = mk_sponsor()
    pid = mk_problem(s)
    a, b = mk_researcher(), mk_researcher()
    ra, rb = send(s, pid, a, b)
    ra, rb = (ra, rb) if ra["researcher_id"] == a["id"] else (rb, ra)
    first = client.post(f"/researcher-requests/{ra['id']}/respond", json={"accept": True}, headers=H(a))
    assert first.status_code == 200 and first.json()["status"] == "accepted"
    prj = first.json()["project_id"]
    assert q("SELECT status FROM researcher_requests WHERE id=?", (rb["id"],))[0]["status"] == "pending"
    second = client.post(f"/researcher-requests/{rb['id']}/respond", json={"accept": True}, headers=H(b))
    assert second.status_code == 200 and second.json()["project_id"] == prj
    roles = {r["researcher_id"]: r["role"] for r in q("SELECT * FROM project_researchers WHERE project_id=?", (prj,))}
    assert roles == {a["id"]: "lead", b["id"]: "researcher"}
    assert q("SELECT researcher_id FROM projects WHERE id=?", (prj,))[0]["researcher_id"] == a["id"]
    assert client.post(f"/researcher-requests/{ra['id']}/respond", json={"accept": True}, headers=H(a)).status_code == 409
    types = {e["type"] for e in q("SELECT type FROM project_events WHERE project_id=?", (prj,))}
    assert {"project_created", "researcher_joined"} <= types
    assert client.get("/researcher/requests", headers=H(b)).json()[0]["project_id"] == prj


def test_request_allowed_when_matched_not_completed():
    s, lead = mk_sponsor(), mk_researcher()
    pid = mk_problem(s)
    mk_project(pid, lead)
    extra = mk_researcher()
    send(s, pid, extra)
    run("UPDATE problems SET status='completed' WHERE id=?", (pid,))
    r = client.post(f"/problems/{pid}/requests", json={"researcher_ids": [mk_researcher()["id"]]}, headers=H(s))
    assert r.status_code == 400 and r.json()["code"] == "BAD_STATE"
    rq = client.get("/researcher/requests", headers=H(extra)).json()[0]
    assert client.post(f"/researcher-requests/{rq['id']}/respond", json={"accept": True}, headers=H(extra)).status_code == 409
    assert q("SELECT status FROM researcher_requests WHERE id=?", (rq["id"],))[0]["status"] == "expired"


def test_permissions():
    s, s2, a, b, st = mk_sponsor(), mk_sponsor(), mk_researcher(), mk_researcher(), mk_student()
    pid = mk_problem(s)
    assert client.get(f"/problems/{pid}/matches", headers=H(s2)).status_code == 403
    assert client.get(f"/problems/{pid}/matches", headers=H(a)).status_code == 403
    assert client.post(f"/problems/{pid}/requests", json={"researcher_ids": [a["id"]]}, headers=H(s2)).status_code == 403
    rq = send(s, pid, a)[0]
    assert client.post(f"/researcher-requests/{rq['id']}/respond", json={"accept": True}, headers=H(b)).status_code == 403
    assert client.get("/researcher/requests", headers=H(st)).status_code == 403
    d = client.post(f"/researcher-requests/{rq['id']}/respond", json={"accept": False}, headers=H(a))
    assert d.json() == {"status": "declined", "project_id": None}
    assert q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND type='researcher_declined'", (s["id"],))[0]["c"] == 1
