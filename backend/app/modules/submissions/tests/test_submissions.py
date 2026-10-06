import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "acc3_v2.db")
os.environ["UPLOAD_DIR"] = os.path.join(tempfile.mkdtemp(), "uploads")
os.environ["LLM_MOCK"] = "true"

import json
import random

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.db import get_conn, init_db, new_id, now
from app.main import app

TABLES = ["notifications", "project_events", "integrity_events", "file_chunks", "submission_files",
          "project_researchers", "profile_likes", "profiles", "ledger_entries", "wallets", "chat_messages",
          "document_chunks", "documents", "quiz_attempts", "quiz_questions", "project_ratings", "rewards",
          "work_submissions", "project_members", "student_requests", "skill_needs", "projects",
          "researcher_requests", "problems", "students", "researchers", "users"]


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


def _wipe():
    init_db()
    conn = get_conn()
    conn.execute("PRAGMA foreign_keys=OFF")
    for t in TABLES:
        conn.execute(f"DELETE FROM {t}")
    return conn


def _user(conn, role, name):
    uid = new_id()
    conn.execute("INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
                 (uid, role, name, f"{uid}@t.com", "x", now()))
    if role == "student":
        conn.execute("INSERT INTO students(user_id, last_active_at) VALUES(?,?)", (uid, now()))
    if role == "researcher":
        conn.execute("INSERT INTO researchers(user_id) VALUES(?)", (uid,))
    return uid


def _make_project(conn, sponsor, lead, co=(), members=(), budget=100000.0, spct=30, rpct=60, ppct=10,
                  status="active"):
    pid, prid = new_id(), new_id()
    conn.execute(
        "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, required_skills, status, "
        "created_at, researcher_pct, project_pct) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (prid, sponsor, "T", "D", budget, spct, "[]", "matched", now(), rpct, ppct))
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)",
                 (pid, prid, lead, status, now()))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, share_pct, joined_at) "
                 "VALUES(?,?,?,?,?)", (pid, lead, "lead", None, now()))
    for c in co:
        conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, share_pct, joined_at) "
                     "VALUES(?,?,?,?,?)", (pid, c, "researcher", None, now()))
    for s in members:
        conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) "
                     "VALUES(?,?,?,?,?)", (pid, s, "python", "active", now()))
    return pid, prid

from app.core.embeddings import chunk_text, embed_texts
from app.modules.submissions.service import heuristic_quality

GOOD = "Implemented login API endpoint with JWT auth validation"


@pytest.fixture()
def env():
    conn = _wipe()
    sponsor, lead, co = _user(conn, "sponsor", "Sp"), _user(conn, "researcher", "Lead"), _user(conn, "researcher", "Co")
    a, b, out = _user(conn, "student", "Ann"), _user(conn, "student", "Ben"), _user(conn, "student", "Out")
    pid, prid = _make_project(conn, sponsor, lead, [co], [a, b])
    yield dict(conn=conn, sponsor=sponsor, lead=lead, co=co, a=a, b=b, out=out, pid=pid, prid=prid,
               c=TestClient(app))
    conn.close()


def _post(e, uid, files=(), paths=None, msg=GOOD, role="student", pid=None, description=None):
    pid = pid or e["pid"]
    url = f"/projects/{pid}/submissions"
    if not files:
        body = {"commit_msg": msg}
        if description:
            body["description"] = description
        return e["c"].post(url, json=body, headers=_h(uid, role))
    data = {"commit_msg": msg}
    if paths is not None:
        data["paths"] = json.dumps(paths)
    fl = [("files", (n, c if isinstance(c, bytes) else c.encode(), "text/plain")) for n, c in files]
    return e["c"].post(url, data=data, files=fl, headers=_h(uid, role))


def _seed_chunks(conn, text, user_id, project_id):
    chunks = chunk_text(" ".join(text.split()), 200, 40)
    for c, v in zip(chunks, embed_texts(chunks)):
        conn.execute("INSERT INTO file_chunks(id, file_id, user_id, project_id, chunk_text, embedding) "
                     "VALUES(?,?,?,?,?,?)", (new_id(), new_id(), user_id, project_id, c, json.dumps(v)))


def test_heuristic_values():
    assert heuristic_quality("fixed stuff") == 0.17
    assert heuristic_quality(GOOD) == 0.65
    assert heuristic_quality("word " * 200) == 1.0


def test_json_submission_hides_score_and_notifies(env):
    r = _post(env, env["a"], description="details")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["ai_quality_score"] is None and b["status"] == "pending" and b["files"] == []
    assert b["originality"] == "original" and b["integrity"] == {"action": "none", "message": ""}
    conn = env["conn"]
    assert conn.execute("SELECT ai_quality_score FROM work_submissions WHERE id=?", (b["id"],)).fetchone()[0] is not None
    assert conn.execute("SELECT COUNT(*) FROM notifications WHERE type='submission_pending' AND user_id=?",
                        (env["lead"],)).fetchone()[0] == 1
    ev = conn.execute("SELECT * FROM project_events WHERE type='submission_created'").fetchone()
    assert json.loads(ev["meta"])["file_count"] == 0


def test_multipart_paths_and_versions(env):
    r = _post(env, env["a"], files=[("main.py", "print('hi')"), ("util.py", "x = 1")],
              paths=["src/app/main.py", "src/lib/util.py"])
    assert r.status_code == 200, r.text
    files = {f["path"]: f for f in r.json()["files"]}
    assert set(files) == {"src/app/main.py", "src/lib/util.py"}
    f = files["src/app/main.py"]
    assert f["name"] == "main.py" and f["version"] == 1 and f["is_text"] is True and f["status"] == "pending"
    assert f["originality"] == "original" and f["is_public"] is False and f["author_name"] == "Ann"
    r2 = _post(env, env["b"], files=[("main.py", "print('v2')")], paths=["src/app/main.py"],
               msg="Refactored main entrypoint to read config from environment")
    assert r2.json()["files"][0]["version"] == 2
    r3 = _post(env, env["a"], files=[("notes.txt", "hello")], msg="Added project notes describing the setup steps")
    assert r3.json()["files"][0]["path"] == "notes.txt"


def test_limits_and_path_rules(env):
    assert _post(env, env["a"], msg="short").status_code == 422
    many = [(f"f{i}.txt", "x") for i in range(31)]
    assert _post(env, env["a"], files=many).status_code == 422
    assert _post(env, env["a"], files=[("big.bin", b"a" * (5 * 1024 * 1024 + 1))]).status_code == 422
    total = [(f"b{i}.bin", b"a" * (4 * 1024 * 1024 + 900000)) for i in range(6)]
    assert _post(env, env["a"], files=total).status_code == 422
    for bad in ("../etc/passwd", "/abs/path.txt", "a//b.txt"):
        r = _post(env, env["a"], files=[("x.txt", "x")], paths=[bad])
        assert r.status_code == 422, bad
    assert env["conn"].execute("SELECT COUNT(*) FROM work_submissions").fetchone()[0] == 0
    ok = _post(env, env["a"], files=[("x.txt", "x")] * 30)
    assert ok.status_code == 200 and len(ok.json()["files"]) == 30


def test_permissions_and_state(env):
    assert _post(env, env["out"]).status_code == 403
    assert _post(env, env["sponsor"], role="sponsor").status_code == 403
    assert _post(env, env["lead"], role="researcher").status_code == 403
    env["conn"].execute("UPDATE project_members SET status='removed' WHERE student_id=?", (env["b"],))
    assert _post(env, env["b"]).status_code == 403
    env["conn"].execute("UPDATE projects SET status='completed' WHERE id=?", (env["pid"],))
    r = _post(env, env["a"])
    assert r.status_code == 400 and r.json()["code"] == "BAD_STATE"


def test_duplicate_guard(env):
    assert _post(env, env["a"]).status_code == 200
    r = _post(env, env["a"])
    assert r.status_code == 409 and r.json()["code"] == "DUPLICATE_SUBMISSION"
    assert _post(env, env["b"]).status_code == 200


def test_originality_rules(env):
    conn = env["conn"]
    text = _words(1)
    # other user's text in ANOTHER project -> copied
    other_pid = new_id()
    _seed_chunks(conn, text, env["out"], other_pid)
    r = _post(env, env["a"], files=[("essay.txt", text)])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["originality"] == "copied" and body["files"][0]["originality"] == "copied"
    assert body["integrity"]["action"] == "warned" and "first warning" in body["integrity"]["message"]
    assert body["status"] == "pending"
    assert conn.execute("SELECT COUNT(*) FROM integrity_events WHERE action='warned'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notifications WHERE type='integrity_warning' AND user_id=?",
                        (env["a"],)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notifications WHERE type='integrity_alert' AND user_id IN (?,?,?)",
                        (env["lead"], env["co"], env["sponsor"])).fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM project_events WHERE type LIKE 'integrity%'").fetchone()[0] == 0


def test_same_user_and_same_project_not_flagged(env):
    conn = env["conn"]
    t1, t2 = _words(2), _words(3)
    _seed_chunks(conn, t1, env["a"], new_id())          # same user, other project
    _seed_chunks(conn, t2, env["b"], env["pid"])        # other user, same project
    r1 = _post(env, env["a"], files=[("a.txt", t1)])
    assert r1.json()["originality"] == "original" and r1.json()["integrity"]["action"] == "none"
    r2 = _post(env, env["a"], files=[("b.txt", t2)], msg="Wrote the second chapter with detailed analysis")
    assert r2.json()["originality"] == "original"
    assert conn.execute("SELECT COUNT(*) FROM file_chunks WHERE user_id=?", (env["a"],)).fetchone()[0] >= 2 + 0


def test_corpus_documents_count(env):
    conn = env["conn"]
    text = _words(4)
    did = new_id()
    conn.execute("INSERT INTO documents(id, project_id, user_id, filename, text, plagiarism_score, created_at) "
                 "VALUES(?,?,?,?,?,?,?)", (did, None, env["out"], "seed.txt", text, 0, now()))
    chunks = chunk_text(text, 200, 40)
    for c, v in zip(chunks, embed_texts(chunks)):
        conn.execute("INSERT INTO document_chunks(id, document_id, chunk_text, embedding) VALUES(?,?,?,?)",
                     (new_id(), did, c, json.dumps(v)))
    assert _post(env, env["a"], files=[("c.txt", text)]).json()["originality"] == "copied"


def test_second_offence_blocks(env):
    conn = env["conn"]
    text = _words(5)
    _seed_chunks(conn, text, env["out"], new_id())
    conn.execute("INSERT INTO integrity_events(id, user_id, project_id, submission_id, action, detail, created_at) "
                 "VALUES(?,?,?,?,?,?,?)", (new_id(), env["a"], env["pid"], None, "warned", "earlier", now()))
    conn.execute("INSERT INTO student_requests(id, project_id, student_id, skill, match_score, status, created_at) "
                 "VALUES(?,?,?,?,?,?,?)", (new_id(), env["pid"], env["a"], "sql", 0.5, "pending", now()))
    r = _post(env, env["a"], files=[("c.txt", text)])
    assert r.status_code == 403 and r.json()["code"] == "BLACKLISTED"
    assert conn.execute("SELECT is_blacklisted FROM users WHERE id=?", (env["a"],)).fetchone()[0] == 1
    m = conn.execute("SELECT status, removed_reason FROM project_members WHERE student_id=?", (env["a"],)).fetchone()
    assert m["status"] == "blacklisted" and m["removed_reason"] == "blacklisted"
    assert conn.execute("SELECT status FROM student_requests").fetchone()[0] == "expired"
    assert conn.execute("SELECT COUNT(*) FROM work_submissions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM submission_files").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM integrity_events WHERE action='blocked'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=?", (env["lead"],)).fetchone()[0] >= 1


def test_list_everyone_sees_all_scores_only_for_researchers(env):
    _post(env, env["a"])
    _post(env, env["b"], msg="Wrote SQL schema migration for the reports database")
    c, pid = env["c"], env["pid"]
    for uid, role in ((env["sponsor"], "sponsor"), (env["a"], "student"), (env["lead"], "researcher"),
                      (env["co"], "researcher")):
        rows = c.get(f"/projects/{pid}/submissions", headers=_h(uid, role)).json()
        assert len(rows) == 2, role
        if role in ("researcher",):
            assert all(s["ai_quality_score"] is not None for s in rows)
        else:
            assert all(s["ai_quality_score"] is None for s in rows)
    assert c.get(f"/projects/{pid}/submissions", headers=_h(env["out"], "student")).status_code == 403
    only = c.get(f"/projects/{pid}/submissions?student_id={env['b']}", headers=_h(env["lead"], "researcher")).json()
    assert len(only) == 1 and only[0]["student_name"] == "Ben"
    env["conn"].execute("UPDATE project_members SET status='removed' WHERE student_id=?", (env["b"],))
    assert len(c.get(f"/projects/{pid}/submissions", headers=_h(env["lead"], "researcher")).json()) == 2


def test_review_rules_and_public_files(env):
    c = env["c"]
    sid = _post(env, env["a"], files=[("a.txt", "alpha"), ("b.txt", "beta")]).json()
    fids = [f["id"] for f in sid["files"]]
    sid = sid["id"]
    other = _post(env, env["b"], files=[("o.txt", "other")], msg="Added extra module with extra tests").json()
    for uid, role in ((env["a"], "student"), (env["sponsor"], "sponsor"), (env["out"], "student")):
        assert c.post(f"/submissions/{sid}/review", json={"approve": True}, headers=_h(uid, role)).status_code == 403
    bad = c.post(f"/submissions/{sid}/review", json={"approve": True, "public_file_ids": [other["files"][0]["id"]]},
                 headers=_h(env["lead"], "researcher"))
    assert bad.status_code == 400 and bad.json()["code"] == "BAD_STATE"
    rej = c.post(f"/submissions/{sid}/review", json={"approve": False, "public_file_ids": [fids[0]]},
                 headers=_h(env["lead"], "researcher"))
    assert rej.status_code == 400
    env["conn"].execute("UPDATE submission_files SET originality='copied' WHERE id=?", (fids[1],))
    assert c.post(f"/submissions/{sid}/review", json={"approve": True, "public_file_ids": [fids[1]]},
                  headers=_h(env["lead"], "researcher")).status_code == 400
    ok = c.post(f"/submissions/{sid}/review", json={"approve": True, "feedback": "nice", "public_file_ids": [fids[0]]},
                headers=_h(env["co"], "researcher"))
    assert ok.status_code == 200, ok.text
    b = ok.json()
    assert b["status"] == "approved" and b["reviewer_feedback"] == "nice" and b["ai_quality_score"] is not None
    pub = {f["id"]: f for f in b["files"]}
    assert pub[fids[0]]["is_public"] is True and pub[fids[0]]["status"] == "approved"
    assert pub[fids[1]]["is_public"] is False
    conn = env["conn"]
    assert conn.execute("SELECT COUNT(*) FROM project_events WHERE type='files_published'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM project_events WHERE type='submission_approved'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notifications WHERE type='submission_approved' AND user_id=?",
                        (env["a"],)).fetchone()[0] == 1
    again = c.post(f"/submissions/{sid}/review", json={"approve": False}, headers=_h(env["lead"], "researcher"))
    assert again.status_code == 409 and again.json()["code"] == "CONFLICT"
