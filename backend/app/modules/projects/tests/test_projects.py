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


def setup(budget=1000.0, pct=40, rpct=None, ppct=0):
    s, r = mk_sponsor(), mk_researcher(name="Lead")
    pid = mk_problem(s, budget, pct, rpct=rpct, ppct=ppct)
    return s, r, pid, mk_project(pid, r)


def test_multi_researcher_listing_and_detail():
    s, lead, pid, prj = setup()
    co = mk_researcher(name="Co")
    add_researcher(prj, co)
    st, gone, other = mk_student(), mk_student(), mk_student()
    add_member(prj, st, "python")
    add_member(prj, gone, "sql", "removed")
    for u in (s, lead, co, st):
        assert [p["id"] for p in client.get("/projects", headers=H(u)).json()] == [prj]
    assert client.get("/projects", headers=H(gone)).json() == []
    assert client.get("/projects", headers=H(other)).json() == []
    p = client.get("/projects", headers=H(s)).json()[0]
    assert p["member_count"] == 1 and p["researcher"]["id"] == lead["id"]
    assert [x["role"] for x in p["researchers"]] == ["lead", "researcher"]
    d = client.get(f"/projects/{prj}", headers=H(co)).json()
    assert d["my_role"] == "researcher" and d["can_manage"] is True
    assert [m["student_id"] for m in d["members"]] == [st["id"]]
    assert [(x["role"], x["share_pct"]) for x in d["researchers"]] == [("lead", 50.0), ("researcher", 50.0)]
    assert client.get(f"/projects/{prj}", headers=H(s)).json()["my_role"] == "sponsor"
    assert client.get(f"/projects/{prj}", headers=H(st)).json()["my_role"] == "student"
    assert client.get(f"/projects/{prj}", headers=H(gone)).status_code == 403


def test_budget_three_way_split_and_equal_share_remainder():
    s, lead, pid, prj = setup(1000.0, 50, rpct=30, ppct=20)
    add_researcher(prj, mk_researcher())
    add_researcher(prj, mk_researcher())
    d = client.get(f"/projects/{prj}", headers=H(lead)).json()
    assert d["budget"] == {"total": 1000.0, "student_pool": 500.0, "researcher_pool": 300.0, "project_fund": 200.0, "researcher_share": 300.0}
    assert [x["share_pct"] for x in d["researchers"]] == [33.34, 33.33, 33.33]


def test_non_member_403_404():
    s, r, pid, prj = setup()
    assert client.get(f"/projects/{prj}", headers=H(mk_student())).status_code == 403
    assert client.get(f"/projects/{prj}", headers=H(mk_sponsor())).status_code == 403
    assert client.get(f"/projects/{prj}", headers=H(mk_researcher())).status_code == 403
    assert client.get(f"/projects/{new_id()}", headers=H(r)).status_code == 404
    assert client.post(f"/projects/{prj}/skill-needs", json=[{"skill": "sql", "count": 1}], headers=H(mk_researcher())).status_code == 403


def test_replace_then_upsert_and_floor_active_only():
    s, r, pid, prj = setup()
    co = mk_researcher()
    add_researcher(prj, co)
    url = f"/projects/{prj}/skill-needs"
    assert len(client.post(url, json=[{"skill": "python", "count": 2}, {"skill": "sql", "count": 1}], headers=H(co)).json()) == 2
    b = client.post(url, json=[{"skill": "ml", "count": 3}], headers=H(r))
    assert [n["skill"] for n in b.json()] == ["ml"]
    st, old = mk_student(("ml",)), mk_student(("ml",))
    run("INSERT INTO student_requests(id,project_id,student_id,skill,match_score,status,created_at) VALUES(?,?,?,?,?,?,?)", (new_id(), prj, st["id"], "ml", 0.5, "accepted", now()))
    add_member(prj, st, "ml")
    add_member(prj, old, "ml", "removed")
    c = client.post(url, json=[{"skill": "react", "count": 2}, {"skill": "ml", "count": 5}], headers=H(r))
    assert {n["skill"]: (n["count"], n["filled"]) for n in c.json()} == {"ml": (5, 1), "react": (2, 0)}
    assert client.post(url, json=[{"skill": "ml", "count": 1}], headers=H(r)).status_code == 200
    add_member(prj, mk_student(("ml",)), "ml")
    bad = client.post(url, json=[{"skill": "ml", "count": 1}], headers=H(r))
    assert bad.status_code == 400 and bad.json()["code"] == "BAD_STATE"


def test_validation_and_inactive():
    s, r, pid, prj = setup()
    url = f"/projects/{prj}/skill-needs"
    assert client.post(url, json=[{"skill": "x", "count": 1}], headers=H(r)).status_code == 422
    assert client.post(url, json=[{"skill": "sql", "count": 1}, {"skill": "sql", "count": 2}], headers=H(r)).status_code == 422
    assert client.post(url, json=[{"skill": "sql", "count": 11}], headers=H(r)).status_code == 422
    run("UPDATE projects SET status='completed' WHERE id=?", (prj,))
    assert client.post(url, json=[{"skill": "sql", "count": 1}], headers=H(r)).status_code == 400


def test_member_removal_frees_slot():
    s, r, pid, prj = setup()
    run("INSERT INTO skill_needs(id,project_id,skill,count) VALUES(?,?,?,?)", (new_id(), prj, "python", 1))
    st = mk_student()
    add_member(prj, st, "python")
    run("INSERT INTO student_requests(id,project_id,student_id,skill,match_score,status,created_at) VALUES(?,?,?,?,?,?,?)", (new_id(), prj, st["id"], "python", 0.5, "pending", now()))
    assert client.get(f"/projects/{prj}", headers=H(r)).json()["skill_needs"][0]["filled"] == 1
    assert client.delete(f"/projects/{prj}/members/{st['id']}", headers=H(mk_student())).status_code == 403
    ok = client.delete(f"/projects/{prj}/members/{st['id']}", headers=H(r))
    assert ok.status_code == 200 and ok.json() == {"status": "removed"}
    d = client.get(f"/projects/{prj}", headers=H(r)).json()
    assert d["skill_needs"][0]["filled"] == 0 and d["members"] == []
    row = q("SELECT status, removed_reason FROM project_members WHERE student_id=?", (st["id"],))[0]
    assert row["status"] == "removed" and row["removed_reason"] == "removed_by_researcher"
    assert q("SELECT status FROM student_requests WHERE student_id=?", (st["id"],))[0]["status"] == "expired"
    assert q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND type='removed_from_project'", (st["id"],))[0]["c"] == 1
    assert client.delete(f"/projects/{prj}/members/{st['id']}", headers=H(r)).status_code == 404
    assert client.get(f"/projects/{prj}", headers=H(st)).status_code == 403


def test_researcher_shares():
    s, lead, pid, prj = setup()
    co = mk_researcher()
    add_researcher(prj, co)
    url = f"/projects/{prj}/researcher-shares"
    body = [{"researcher_id": lead["id"], "share_pct": 70}, {"researcher_id": co["id"], "share_pct": 30}]
    assert client.put(url, json=body, headers=H(co)).status_code == 403
    assert client.put(url, json=body[:1], headers=H(lead)).status_code == 422
    assert client.put(url, json=[body[0], {"researcher_id": co["id"], "share_pct": 20}], headers=H(lead)).status_code == 422
    assert client.put(url, json=[body[0], {"researcher_id": new_id(), "share_pct": 30}], headers=H(lead)).status_code == 422
    ok = client.put(url, json=body, headers=H(lead))
    assert ok.status_code == 200 and [(x["role"], x["share_pct"]) for x in ok.json()] == [("lead", 70.0), ("researcher", 30.0)]
    d = client.get(f"/projects/{prj}", headers=H(lead)).json()
    assert [x["share_pct"] for x in d["researchers"]] == [70.0, 30.0]
    assert q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND type='shares_changed'", (co["id"],))[0]["c"] == 1


def test_counts():
    s, lead, pid, prj = setup()
    st, st2 = mk_student(), mk_student()
    add_member(prj, st, "python")
    add_member(prj, st2, "python")
    for who, status in ((st, "pending"), (st, "approved"), (st2, "pending")):
        run("INSERT INTO work_submissions(id,project_id,student_id,commit_msg,status,created_at) VALUES(?,?,?,?,?,?)", (new_id(), prj, who["id"], "commit message ok", status, now()))
    run("INSERT INTO student_requests(id,project_id,student_id,skill,match_score,status,created_at) VALUES(?,?,?,?,?,?,?)", (new_id(), prj, mk_student()["id"], "python", 0.5, "pending", now()))
    assert client.get(f"/projects/{prj}/counts", headers=H(lead)).json() == {"pending_approvals": 2, "my_pending_submissions": 0, "pending_student_requests": 1}
    assert client.get(f"/projects/{prj}/counts", headers=H(st)).json() == {"pending_approvals": 0, "my_pending_submissions": 1, "pending_student_requests": 0}
    assert client.get(f"/projects/{prj}/counts", headers=H(s)).json()["pending_approvals"] == 2
    assert client.get(f"/projects/{prj}/counts", headers=H(mk_student())).status_code == 403
