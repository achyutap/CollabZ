import json
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "explore_test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["LLM_MOCK"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import get_conn, init_db, new_id, now  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def mk(conn, role, name, skills=(), bl=0, headline=""):
    uid = new_id()
    conn.execute("INSERT INTO users(id, role, name, email, password_hash, created_at, is_blacklisted) VALUES(?,?,?,?,?,?,?)", (uid, role, name, f"{uid}@t.com", "x", now(), bl))
    if role == "student":
        conn.execute("INSERT INTO students(user_id, skills, temp_rating, last_active_at) VALUES(?,?,?,?)", (uid, json.dumps(list(skills)), 3.5, now()))
    if role == "researcher":
        conn.execute("INSERT INTO researchers(user_id, skills, rating) VALUES(?,?,?)", (uid, json.dumps(list(skills)), 4.6))
    if headline:
        conn.execute("INSERT INTO profiles(user_id, headline, updated_at) VALUES(?,?,?)", (uid, headline, now()))
    return uid, {"Authorization": "Bearer " + create_access_token(uid, role)}


def test_explore_people_and_projects():
    conn = get_conn()
    sp, sph = mk(conn, "sponsor", "Zed Sponsor")
    rs, rsh = mk(conn, "researcher", "Alice Researcher", ["iot"], headline="Embedded systems expert")
    st, sth = mk(conn, "student", "Bob Student", ["python"])
    bad, _ = mk(conn, "student", "Blocked Bob", ["python"], bl=1)
    out, outh = mk(conn, "student", "Outsider", ["sql"])
    conn.execute("INSERT INTO profile_likes(liker_id, user_id, created_at) VALUES(?,?,?)", (st, rs, now()))
    pubp, pubprj, hidp, hidprj = new_id(), new_id(), new_id(), new_id()
    for pid, prj, title in ((pubp, pubprj, "Water Quality IoT"), (hidp, hidprj, "Secret Project")):
        conn.execute(
            "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, required_skills, status, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (pid, sp, title, "Sensors " * 60, 5000, 30, '["iot","python"]', "matched", now()),
        )
        conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)", (prj, pid, rs, "active", now()))
        conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, joined_at) VALUES(?,?,?,?)", (prj, rs, "lead", now()))
        conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) VALUES(?,?,?,?,?)", (prj, st, "python", "active", now()))
        sid = new_id()
        conn.execute("INSERT INTO work_submissions(id, project_id, student_id, commit_msg, status, created_at) VALUES(?,?,?,?,?,?)", (sid, prj, st, "commit message ok", "approved", now()))
        conn.execute(
            "INSERT INTO submission_files(id, submission_id, project_id, author_id, path, name, size, content_type, is_text, storage_path, version, is_public, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (new_id(), sid, prj, st, "a.py", "a.py", 1, "text/plain", 1, "x", 1, 1 if pid == pubp else 0, now()),
        )
    conn.close()

    ppl = client.get("/explore/people", headers=outh).json()
    names = [p["name"] for p in ppl]
    assert "Blocked Bob" not in names and names[0] == "Alice Researcher" and ppl[0]["likes_count"] == 1 and ppl[0]["rating"] == 4.6
    assert [p["name"] for p in client.get("/explore/people?q=embedded", headers=outh).json()] == ["Alice Researcher"]
    assert all(p["role"] == "student" for p in client.get("/explore/people?role=student", headers=outh).json())
    assert client.get("/explore/people?role=wizard", headers=outh).status_code == 422

    cards = client.get("/explore/projects", headers=outh).json()
    assert [c["title"] for c in cards] == ["Water Quality IoT"] and len(cards[0]["summary"]) == 200
    assert cards[0]["public_file_count"] == 1 and cards[0]["members"][0]["name"] == "Bob Student"
    assert client.get("/explore/projects?skill=sql", headers=outh).json() == []
    assert len(client.get("/explore/projects?q=water&skill=iot", headers=outh).json()) == 1

    d = client.get(f"/explore/projects/{pubprj}", headers=outh)
    assert d.status_code == 200 and "budget" not in json.dumps(d.json()) and len(d.json()["files"]) == 1
    assert client.get(f"/explore/projects/{hidprj}", headers=outh).status_code == 404
    assert client.get(f"/explore/projects/{hidprj}", headers=sph).status_code == 200  # project person
    assert client.get(f"/explore/projects/{new_id()}", headers=outh).status_code == 404
