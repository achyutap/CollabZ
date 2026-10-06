import os
import random
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "acc3_plag.db")
os.environ["LLM_MOCK"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.db import get_conn, init_db, new_id, now
from app.main import app
from app.modules.plagiarism.service import verdict_for

TABLES = ["ledger_entries", "wallets", "chat_messages", "document_chunks", "documents", "quiz_attempts",
          "quiz_questions", "project_ratings", "rewards", "work_submissions", "project_members",
          "student_requests", "skill_needs", "projects", "researcher_requests", "problems", "students",
          "researchers", "users"]


def _words(seed, n=250):
    rng = random.Random(seed)
    return " ".join(f"term{rng.randrange(5000)}x{seed}" for _ in range(n))


def _token(uid, role):
    try:
        return security.create_access_token(uid, role)
    except TypeError:
        return security.create_access_token({"sub": uid, "role": role})


def _h(uid, role):
    return {"Authorization": f"Bearer {_token(uid, role)}"}


def _user(conn, role, name):
    uid = new_id()
    conn.execute("INSERT INTO users VALUES(?,?,?,?,?,?)", (uid, role, name, f"{uid}@t.com", "x", now()))
    if role == "student":
        conn.execute("INSERT INTO students(user_id, last_active_at) VALUES(?,?)", (uid, now()))
    return uid


@pytest.fixture()
def env():
    init_db()
    conn = get_conn()
    conn.execute("PRAGMA foreign_keys=OFF")
    for t in TABLES:
        conn.execute(f"DELETE FROM {t}")
    sponsor, res = _user(conn, "sponsor", "Sp"), _user(conn, "researcher", "Res")
    a, b, out = _user(conn, "student", "Ann"), _user(conn, "student", "Ben"), _user(conn, "student", "Out")
    pid, prid = new_id(), new_id()
    conn.execute("INSERT INTO problems VALUES(?,?,?,?,?,?,?,?,?)",
                 (prid, sponsor, "T", "D", 1000.0, 30, "[]", "matched", now()))
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)",
                 (pid, prid, res, "active", now()))
    for s in (a, b):
        conn.execute("INSERT INTO project_members VALUES(?,?,?)", (pid, s, "python"))
    yield dict(conn=conn, sponsor=sponsor, res=res, a=a, b=b, out=out, pid=pid, c=TestClient(app))
    conn.close()


def _upload(e, uid, text, role="student", filename="doc.txt"):
    return e["c"].post(f"/projects/{e['pid']}/documents", json={"filename": filename, "text": text},
                       headers=_h(uid, role))


def test_verdict_boundaries():
    assert verdict_for(0) == "clean" and verdict_for(14.9) == "clean"
    assert verdict_for(15) == "suspicious" and verdict_for(40) == "suspicious"
    assert verdict_for(40.1) == "likely_copied" and verdict_for(100) == "likely_copied"


def test_identical_text_from_other_user_is_flagged(env):
    text = _words(1)
    r1 = _upload(env, env["a"], text)
    assert r1.status_code == 200, r1.text
    assert r1.json()["verdict"] == "clean" and r1.json()["matches"] == []
    r2 = _upload(env, env["b"], text, filename="copy.txt")
    body = r2.json()
    assert body["verdict"] == "likely_copied" and body["plagiarism_score"] == 100.0
    assert body["total_chunks"] >= 2 and len(body["matches"]) == body["total_chunks"]
    m = body["matches"][0]
    assert m["source_document_id"] == r1.json()["document_id"] and m["source_user_name"] == "Ann"
    assert m["similarity"] >= 0.85 and m["chunk_text"] and m["matched_text"]


def test_same_user_resubmission_not_flagged(env):
    text = _words(2)
    _upload(env, env["a"], text)
    r = _upload(env, env["a"], text)
    assert r.status_code == 200 and r.json()["matches"] == [] and r.json()["verdict"] == "clean"


def test_unrelated_text_clean(env):
    _upload(env, env["a"], _words(3))
    r = _upload(env, env["b"], _words(4))
    assert r.json()["verdict"] == "clean" and r.json()["plagiarism_score"] == 0


def test_short_text_rejected(env):
    r = _upload(env, env["a"], "too few words here")
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"


def test_multipart_txt_and_bad_extension(env):
    c, pid = env["c"], env["pid"]
    ok = c.post(f"/projects/{pid}/documents", files={"file": ("a.txt", _words(5).encode(), "text/plain")},
                headers=_h(env["a"], "student"))
    assert ok.status_code == 200, ok.text
    bad = c.post(f"/projects/{pid}/documents", files={"file": ("a.exe", b"x " * 200, "application/octet-stream")},
                 headers=_h(env["a"], "student"))
    assert bad.status_code == 422
    big = c.post(f"/projects/{pid}/documents", files={"file": ("a.txt", b"a " * (3 * 1024 * 1024), "text/plain")},
                 headers=_h(env["a"], "student"))
    assert big.status_code == 422


def test_access_control_list_and_get(env):
    text = _words(6)
    d1 = _upload(env, env["a"], text).json()["document_id"]
    _upload(env, env["b"], _words(7))
    c, pid = env["c"], env["pid"]
    assert _upload(env, env["sponsor"], text, role="sponsor").status_code == 403
    assert _upload(env, env["out"], text).status_code == 403
    assert c.get(f"/projects/{pid}/documents", headers=_h(env["sponsor"], "sponsor")).status_code == 403
    mine = c.get(f"/projects/{pid}/documents", headers=_h(env["a"], "student")).json()
    assert len(mine) == 1 and mine[0]["user_name"] == "Ann"
    allv = c.get(f"/projects/{pid}/documents", headers=_h(env["res"], "researcher")).json()
    assert len(allv) == 2 and allv[0]["created_at"] >= allv[1]["created_at"]
    assert c.get(f"/documents/{d1}", headers=_h(env["a"], "student")).status_code == 200
    assert c.get(f"/documents/{d1}", headers=_h(env["res"], "researcher")).status_code == 200
    assert c.get(f"/documents/{d1}", headers=_h(env["b"], "student")).status_code == 403
    assert c.get(f"/documents/{d1}", headers=_h(env["sponsor"], "sponsor")).status_code == 403


def test_get_document_recomputes_only_earlier_docs(env):
    text = _words(8)
    d1 = _upload(env, env["a"], text).json()["document_id"]
    d2 = _upload(env, env["b"], text).json()["document_id"]
    c = env["c"]
    first = c.get(f"/documents/{d1}", headers=_h(env["a"], "student")).json()
    second = c.get(f"/documents/{d2}", headers=_h(env["b"], "student")).json()
    assert first["matches"] == []
    assert len(second["matches"]) == second["total_chunks"] and second["verdict"] == "likely_copied"
