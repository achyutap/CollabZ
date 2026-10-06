import json
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "profiles_test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["LLM_MOCK"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import get_conn, init_db, new_id, now  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def mk(conn, role, name, skills=(), pending=(), done=0, final=None, temp=None):
    uid = new_id()
    conn.execute("INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)", (uid, role, name, f"{uid}@t.com", "x", now()))
    if role == "student":
        conn.execute(
            "INSERT INTO students(user_id, skills, pending_skills, temp_rating, final_rating, projects_done, last_active_at) VALUES(?,?,?,?,?,?,?)",
            (uid, json.dumps(list(skills)), json.dumps(list(pending)), temp, final, done, now()),
        )
    if role == "researcher":
        conn.execute("INSERT INTO researchers(user_id, skills, rating) VALUES(?,?,?)", (uid, json.dumps(list(skills)), 4.2))
    return uid, {"Authorization": "Bearer " + create_access_token(uid, role)}


@pytest.fixture()
def w():
    conn = get_conn()
    sp, sph = mk(conn, "sponsor", "Sponsor One")
    rs, rsh = mk(conn, "researcher", "Res One", skills=["python"])
    st, sth = mk(conn, "student", "Stu One", skills=["sql"], pending=["ml"], done=1, final=4.4, temp=3.0)
    st0, st0h = mk(conn, "student", "Stu Zero", skills=["sql"], done=0, temp=3.5)
    pid, prj = new_id(), new_id()
    conn.execute(
        "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, required_skills, status, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (pid, sp, "Proj", "D", 100, 30, "[]", "matched", now()),
    )
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)", (prj, pid, rs, "active", now()))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, joined_at) VALUES(?,?,?,?)", (prj, rs, "lead", now()))
    conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) VALUES(?,?,?,?,?)", (prj, st, "sql", "removed", now()))
    conn.close()
    return dict(sp=sph, rs=rsh, st=sth, st0=st0h, st_id=st, st0_id=st0, rs_id=rs, sp_id=sp, prj=prj)


def test_profile_rating_rule_pending_only_for_self_and_works_visibility(w):
    own = client.get("/me/profile", headers=w["st"]).json()
    assert own["is_me"] and own["rating"] == 4.4 and own["pending_skills"] == ["ml"] and own["projects_done"] == 1
    assert len(own["works"]) == 1 and own["works"][0]["my_role"] == "student" and own["works"][0]["skill"] == "sql"
    seen = client.get(f"/users/{w['st_id']}/profile", headers=w["sp"]).json()
    assert seen["pending_skills"] == [] and seen["works"] == [] and seen["is_me"] is False
    assert client.get(f"/users/{w['st0_id']}/profile", headers=w["sp"]).json()["rating"] == 3.5
    conn = get_conn()
    conn.execute("INSERT INTO work_submissions(id, project_id, student_id, commit_msg, status, created_at) VALUES('s1',?,?,'a commit msg','approved',?)", (w["prj"], w["st_id"], now()))
    conn.execute(
        "INSERT INTO submission_files(id, submission_id, project_id, author_id, path, name, size, content_type, is_text, storage_path, is_public, created_at) VALUES('f1','s1',?,?, 'a.py','a.py',1,'text/plain',1,'x',1,?)",
        (w["prj"], w["st_id"], now()),
    )
    conn.close()
    assert len(client.get(f"/users/{w['st_id']}/profile", headers=w["sp"]).json()["works"]) == 1
    assert client.get(f"/users/{new_id()}/profile", headers=w["sp"]).status_code == 404


def test_patch_validation(w):
    h = w["st"]
    assert client.patch("/me/profile", json={"headline": "x" * 121}, headers=h).status_code == 422
    assert client.patch("/me/profile", json={"about": "x" * 2001}, headers=h).status_code == 422
    assert client.patch("/me/profile", json={"name": "A"}, headers=h).status_code == 422
    assert client.patch("/me/profile", json={"links": {"github": "ftp://x"}}, headers=h).status_code == 422
    assert client.patch("/me/profile", json={"links": {"github": "javascript:alert(1)"}}, headers=h).status_code == 422
    assert client.patch("/me/profile", json={"details": {"k": "x" * 21000}}, headers=h).status_code == 422
    assert client.patch("/me/profile", json={"add_skills": ["cobol"]}, headers=h).status_code == 422
    r = client.patch(
        "/me/profile",
        json={"name": "Stu Renamed", "headline": "Builder", "links": {"github": "https://github.com/x"}, "details": {"interests": ["iot"]}},
        headers=h,
    )
    assert r.status_code == 200
    b = r.json()
    assert b["user"]["name"] == "Stu Renamed" and b["headline"] == "Builder" and b["links"] == {"github": "https://github.com/x"} and b["details"] == {"interests": ["iot"]}


def test_student_skill_changes_go_to_pending(w):
    r = client.patch("/me/profile", json={"add_skills": ["sql", "ml", "react", "python"]}, headers=w["st"]).json()
    assert r["skills"] == ["sql"] and r["pending_skills"] == ["ml", "react", "python"]
    r = client.patch("/me/profile", json={"remove_skills": ["ml", "sql"]}, headers=w["st"]).json()
    assert r["skills"] == [] and r["pending_skills"] == ["react", "python"]


def test_researcher_skills_direct_min_one_and_sponsor_ignored(w):
    r = client.patch("/me/profile", json={"add_skills": ["sql"]}, headers=w["rs"]).json()
    assert r["skills"] == ["python", "sql"]
    bad = client.patch("/me/profile", json={"remove_skills": ["python", "sql"]}, headers=w["rs"])
    assert bad.status_code == 422
    ok = client.patch("/me/profile", json={"add_skills": ["ml"], "headline": "Hi"}, headers=w["sp"])
    assert ok.status_code == 200 and ok.json()["skills"] == []


def test_likes(w):
    r = client.post(f"/users/{w['st_id']}/like", headers=w["rs"]).json()
    assert r == {"likes_count": 1, "liked_by_me": True}
    client.post(f"/users/{w['st_id']}/like", headers=w["rs"])
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='profile_like'", (w["st_id"],)).fetchone()[0]
    conn.close()
    assert n == 1
    assert client.post(f"/users/{w['st_id']}/like", headers=w["st"]).status_code == 400
    assert client.delete(f"/users/{w['st_id']}/like", headers=w["rs"]).json() == {"likes_count": 0, "liked_by_me": False}
    assert client.post(f"/users/{new_id()}/like", headers=w["rs"]).status_code == 404
