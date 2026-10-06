import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "files_test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["LLM_MOCK"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import get_conn, init_db, new_id, now  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.core.storage import save_file  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def mk_user(conn, role):
    uid = new_id()
    conn.execute(
        "INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
        (uid, role, f"{role}-{uid[:4]}", f"{uid}@t.com", "x", now()),
    )
    return uid, {"Authorization": "Bearer " + create_access_token(uid, role)}


def add_file(conn, prj, sub, author, path, version, data, originality="original", public=0, text=1):
    fid = new_id()
    sp = save_file(prj, fid, data)
    conn.execute(
        "INSERT INTO submission_files(id, submission_id, project_id, author_id, path, name, size, content_type, is_text, storage_path, version, originality, is_public, created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (fid, sub, prj, author, path, path.split("/")[-1], len(data), "text/plain", text, sp, version, originality, public, now()),
    )
    return fid


def add_sub(conn, prj, student, status):
    sid = new_id()
    conn.execute(
        "INSERT INTO work_submissions(id, project_id, student_id, commit_msg, status, created_at) VALUES(?,?,?,?,?,?)",
        (sid, prj, student, "a commit message", status, now()),
    )
    return sid


@pytest.fixture()
def w():
    conn = get_conn()
    sp, sph = mk_user(conn, "sponsor")
    lead, leadh = mk_user(conn, "researcher")
    st, sth = mk_user(conn, "student")
    other, otherh = mk_user(conn, "student")
    pid, prj = new_id(), new_id()
    conn.execute(
        "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, required_skills, status, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (pid, sp, "P", "D", 1000, 30, "[]", "matched", now()),
    )
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)", (prj, pid, lead, "active", now()))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, joined_at) VALUES(?,?,?,?)", (prj, lead, "lead", now()))
    conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) VALUES(?,?,?,?,?)", (prj, st, "python", "active", now()))
    s_ok, s_ok2 = add_sub(conn, prj, st, "approved"), add_sub(conn, prj, st, "approved")
    s_rej, s_pen = add_sub(conn, prj, st, "rejected"), add_sub(conn, prj, st, "pending")
    f1 = add_file(conn, prj, s_ok, st, "src/main.py", 1, b"print('v1')\n")
    f2 = add_file(conn, prj, s_ok2, st, "src/main.py", 2, b"print('v2')\n")
    f3 = add_file(conn, prj, s_rej, st, "src/main.py", 3, b"print('rejected')\n")
    f4 = add_file(conn, prj, s_pen, st, "docs/notes.md", 1, b"# notes\n")
    f5 = add_file(conn, prj, s_ok, st, "src/copy.py", 1, b"copied", originality="copied")
    f6 = add_file(conn, prj, s_ok, st, "bin/data.bin", 1, b"\x00\xff\xfe", text=0)
    conn.close()
    return dict(prj=prj, sp=sph, lead=leadh, st=sth, other=otherh, f1=f1, f2=f2, f3=f3, f4=f4, f5=f5, f6=f6, st_id=st)


def test_tree_picks_latest_non_rejected_version(w):
    r = client.get(f"/projects/{w['prj']}/files", headers=w["sp"])
    assert r.status_code == 200
    by = {f["path"]: f for f in r.json()}
    assert by["src/main.py"]["version"] == 2 and by["src/main.py"]["status"] == "approved"
    assert by["docs/notes.md"]["status"] == "pending" and by["docs/notes.md"]["author_name"].startswith("student")
    assert client.get(f"/projects/{w['prj']}/files", headers=w["other"]).status_code == 403


def test_content_download_and_access(w):
    r = client.get(f"/files/{w['f2']}/content", headers=w["st"]).json()
    assert r["content"] == "print('v2')\n" and r["truncated"] is False
    assert client.get(f"/files/{w['f6']}/content", headers=w["lead"]).json()["content"] is None
    d = client.get(f"/files/{w['f2']}/download", headers=w["lead"])
    assert d.content == b"print('v2')\n" and "attachment" in d.headers["content-disposition"]
    assert client.get(f"/files/{w['f2']}/content", headers=w["other"]).status_code == 403
    assert client.get(f"/files/{new_id()}/content", headers=w["lead"]).status_code == 404


def test_visibility_rules_and_public_access(w):
    assert client.patch(f"/files/{w['f2']}/visibility", json={"is_public": True}, headers=w["st"]).status_code == 403
    for bad in (w["f4"], w["f5"], w["f3"]):  # pending, copied, rejected
        r = client.patch(f"/files/{bad}/visibility", json={"is_public": True}, headers=w["lead"])
        assert r.status_code == 400 and r.json()["code"] == "BAD_STATE"
    r = client.patch(f"/files/{w['f2']}/visibility", json={"is_public": True}, headers=w["lead"])
    assert r.status_code == 200 and r.json()["is_public"] is True
    # outsider can now read the public version and only public versions
    assert client.get(f"/files/{w['f2']}/content", headers=w["other"]).status_code == 200
    assert client.get(f"/files/{w['f1']}/content", headers=w["other"]).status_code == 403
    vs = client.get(f"/files/{w['f2']}/versions", headers=w["other"]).json()
    assert [v["version"] for v in vs] == [2]
    vs = client.get(f"/files/{w['f2']}/versions", headers=w["lead"]).json()
    assert [v["version"] for v in vs] == [3, 2, 1]
    conn = get_conn()
    ev = conn.execute("SELECT * FROM project_events WHERE project_id=? AND type='files_published'", (w["prj"],)).fetchall()
    notes = conn.execute("SELECT * FROM notifications WHERE user_id=?", (w["st_id"],)).fetchall()
    conn.close()
    assert len(ev) == 1 and '"count": 1' in ev[0]["meta"] and len(notes) == 1


def test_bulk_visibility_and_unpublish(w):
    r = client.post(f"/projects/{w['prj']}/files/visibility", json={"file_ids": [w["f1"], w["f2"]], "is_public": True}, headers=w["lead"])
    assert r.status_code == 200 and all(f["is_public"] for f in r.json())
    r = client.post(f"/projects/{w['prj']}/files/visibility", json={"file_ids": [w["f2"]], "is_public": False}, headers=w["lead"])
    assert r.json()[0]["is_public"] is False
    conn = get_conn()
    types = [e["type"] for e in conn.execute("SELECT type FROM project_events WHERE project_id=? ORDER BY rowid", (w["prj"],))]
    conn.close()
    assert types == ["files_published", "files_unpublished"]
    r = client.post(f"/projects/{w['prj']}/files/visibility", json={"file_ids": [new_id()], "is_public": True}, headers=w["lead"])
    assert r.status_code == 404
