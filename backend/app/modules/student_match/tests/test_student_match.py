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

from datetime import datetime, timedelta, timezone

from app.modules.student_match.service import score_student


def setup(skill="python", count=1):
    s, r = mk_sponsor(), mk_researcher()
    prj = mk_project(mk_problem(s), r)
    run("INSERT INTO skill_needs(id,project_id,skill,count) VALUES(?,?,?,?)", (new_id(), prj, skill, count))
    return r, prj


def req(r, prj, st, skill="python"):
    return client.post(f"/projects/{prj}/student-requests", json={"student_id": st["id"], "skill": skill}, headers=H(r))


def accept(st, rq, ok=True):
    return client.post(f"/student-requests/{rq['id']}/respond", json={"accept": ok}, headers=H(st))


def test_score_example_and_recency():
    n = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert score_student(True, 4.0, n.isoformat(), n) == 0.5 + 0.32 + 0.1
    assert score_student(True, 4.0, (n - timedelta(days=45)).isoformat(), n) == 0.5 + 0.32 + 0.05
    assert score_student(True, 4.0, (n - timedelta(days=400)).isoformat(), n) == 0.82
    assert score_student(False, 5.0, n.isoformat(), n) == 0.5


def test_ineligible_and_permissions():
    r, prj = setup()
    assert req(r, prj, mk_student(("sql",))).status_code == 400
    bad = req(r, prj, mk_student(("python",)), "ml")
    assert bad.status_code == 400 and "skill needs" in bad.json()["detail"]
    assert req(mk_researcher(), prj, mk_student()).status_code == 403
    assert req(r, prj, mk_student(), "python").status_code == 200
    black = mk_student()
    run("UPDATE users SET is_blacklisted=1 WHERE id=?", (black["id"],))
    assert req(r, prj, black).status_code == 400
    member = mk_student()
    add_member(prj, member, "python")
    assert req(r, prj, member).status_code in (400, 409)


def test_co_researcher_can_invite_and_student_notified():
    r, prj = setup(count=2)
    co = mk_researcher()
    add_researcher(prj, co)
    st = mk_student()
    assert req(co, prj, st).status_code == 200
    assert q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND type='student_request'", (st["id"],))[0]["c"] == 1
    assert len(client.get(f"/projects/{prj}/student-requests", headers=H(co)).json()) == 1


def test_cap_enforcement_and_double_accept():
    r, prj = setup(count=1)
    a, b = mk_student(), mk_student()
    ra, rb = req(r, prj, a).json(), req(r, prj, b).json()
    ok = accept(a, ra)
    assert ok.status_code == 200 and ok.json() == {"status": "accepted"}
    assert accept(a, ra).status_code == 409
    assert q("SELECT status FROM student_requests WHERE id=?", (rb["id"],))[0]["status"] == "expired"
    assert accept(b, rb).status_code == 409
    assert len(q("SELECT * FROM project_members WHERE project_id=? AND status='active'", (prj,))) == 1
    assert req(r, prj, mk_student()).json()["detail"] == "Slots full"
    types = {e["type"] for e in q("SELECT type FROM project_events WHERE project_id=?", (prj,))}
    assert "student_joined" in types
    assert q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND type='student_joined'", (r["id"],))[0]["c"] == 1


def test_accept_when_full_by_race_expires():
    r, prj = setup(count=1)
    a, b = mk_student(), mk_student()
    rb = req(r, prj, b).json()
    add_member(prj, a, "python")
    assert accept(b, rb).status_code == 409
    assert q("SELECT status FROM student_requests WHERE id=?", (rb["id"],))[0]["status"] == "expired"


def test_reinvite_after_removal():
    r, prj = setup(count=1)
    st = mk_student()
    rq = req(r, prj, st).json()
    assert accept(st, rq).status_code == 200
    assert client.delete(f"/projects/{prj}/members/{st['id']}", headers=H(r)).status_code == 200
    ids = [c["student"]["id"] for c in client.get(f"/projects/{prj}/shortlist", headers=H(r)).json()[0]["candidates"]]
    assert st["id"] in ids
    again = req(r, prj, st)
    assert again.status_code == 200 and again.json()["id"] == rq["id"] and again.json()["status"] == "pending"
    assert accept(st, again.json()).status_code == 200
    rows = q("SELECT status, removed_at, joined_at FROM project_members WHERE project_id=? AND student_id=?", (prj, st["id"]))
    assert len(rows) == 1 and rows[0]["status"] == "active" and rows[0]["removed_at"] is None and rows[0]["joined_at"]


def test_decline_and_lists():
    r, prj = setup(count=2)
    a = mk_student()
    rq = req(r, prj, a).json()
    assert req(r, prj, a).status_code == 409
    mine = client.get("/student/requests", headers=H(a)).json()
    assert mine[0]["project_title"] == "Test problem" and mine[0]["researcher_name"] == "Researcher"
    assert accept(mk_student(), rq).status_code == 403
    assert accept(a, rq, False).json() == {"status": "declined"}
    assert q("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND type='student_declined'", (r["id"],))[0]["c"] == 1
    assert req(r, prj, a).status_code == 200


def test_shortlist_rules():
    r, prj = setup(count=1)
    recent = mk_student(temp=4.0)
    stale = mk_student(temp=4.0, last_active=(datetime.now(timezone.utc) - timedelta(days=80)).isoformat())
    unrated, member, wrong, black, removed = mk_student(temp=None), mk_student(temp=5.0), mk_student(("sql",), temp=5.0), mk_student(temp=5.0), mk_student(temp=5.0)
    add_member(prj, member, "python")
    add_member(prj, removed, "python", "removed")
    run("UPDATE users SET is_blacklisted=1 WHERE id=?", (black["id"],))
    run("UPDATE students SET pending_skills=? WHERE user_id=?", (json.dumps(["python"]), wrong["id"]))
    sl = client.get(f"/projects/{prj}/shortlist", headers=H(r)).json()
    assert sl[0]["skill"] == "python" and sl[0]["filled"] == 1 and sl[0]["count"] == 1
    ids = [c["student"]["id"] for c in sl[0]["candidates"]]
    assert len(ids) <= 2
    assert not ({member["id"], unrated["id"], wrong["id"], black["id"]} & set(ids))
    c = sl[0]["candidates"][0]
    assert c["rating_type"] == "temp" and c["student"]["rating"] == c["rating"] and c["student"]["pending_skills"] == []


def test_student_search_filters():
    r, prj = setup()
    a = mk_student(("python", "sql"), temp=4.5, name="Zed Alpha")
    b = mk_student(("ml",), temp=None, name="Zed Beta")
    c = mk_student(("python",), temp=3.0, name="Zed Gamma")
    black = mk_student(("python",), name="Zed Black")
    member = mk_student(("python",), name="Zed Member")
    pend = mk_student(("react",), name="Zed Pending")
    run("UPDATE users SET is_blacklisted=1 WHERE id=?", (black["id"],))
    run("UPDATE students SET pending_skills=? WHERE user_id=?", (json.dumps(["python"]), pend["id"]))
    add_member(prj, member, "python")
    url = f"/projects/{prj}/student-search"
    allz = [s["id"] for s in client.get(url, params={"q": "zed"}, headers=H(r)).json()]
    assert a["id"] in allz and b["id"] in allz and c["id"] in allz
    assert not ({black["id"], member["id"]} & set(allz))
    assert allz.index(a["id"]) < allz.index(c["id"])
    py = [s["id"] for s in client.get(url, params={"q": "zed", "skill": "python"}, headers=H(r)).json()]
    assert set(py) == {a["id"], c["id"]}
    assert [s["id"] for s in client.get(url, params={"q": "beta"}, headers=H(r)).json()] == [b["id"]]
    assert client.get(url, params={"skill": "nope"}, headers=H(r)).status_code == 422
    assert client.get(url, headers=H(mk_student())).status_code == 403
    assert len(client.get(url, headers=H(r)).json()) <= 20
