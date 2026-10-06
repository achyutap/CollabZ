import os
import tempfile

os.environ["LLM_MOCK"] = "true"
os.environ["AUTO_SEED"] = "false"

import pytest

from app.core.access import (
    active_student_ids,
    is_project_researcher,
    lead_id,
    project_role,
    require_project_access,
    researcher_ids,
    sponsor_id,
)
from app.core.db import get_conn, init_db, new_id, now
from app.core.deps import CurrentUser
from app.core.errors import AppError
from app.core.notify import log_event, notify, notify_many
from app.core import storage


@pytest.fixture(scope="module")
def conn():
    d = tempfile.mkdtemp()
    os.environ["DB_PATH"] = os.path.join(d, "v2.db")
    os.environ["UPLOAD_DIR"] = os.path.join(d, "uploads")
    init_db()
    c = get_conn()
    yield c
    c.close()


def mk_user(conn, role):
    uid = new_id()
    conn.execute(
        "INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
        (uid, role, role + uid[:4], uid + "@t.com", "x", now()),
    )
    return uid


@pytest.fixture(scope="module")
def world(conn):
    sp, lead, co, st, gone, out = (mk_user(conn, r) for r in ("sponsor", "researcher", "researcher", "student", "student", "student"))
    pid, prj = new_id(), new_id()
    conn.execute(
        "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, created_at) VALUES(?,?,?,?,?,?,?)",
        (pid, sp, "t", "d", 1000, 50, now()),
    )
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, created_at) VALUES(?,?,?,?)", (prj, pid, lead, now()))
    conn.execute("INSERT INTO project_researchers VALUES(?,?,?,NULL,?)", (prj, lead, "lead", now()))
    conn.execute("INSERT INTO project_researchers VALUES(?,?,?,NULL,?)", (prj, co, "researcher", now()))
    conn.execute("INSERT INTO project_members(project_id, student_id, skill, status) VALUES(?,?,?,?)", (prj, st, "python", "active"))
    conn.execute("INSERT INTO project_members(project_id, student_id, skill, status) VALUES(?,?,?,?)", (prj, gone, "sql", "removed"))
    return dict(sp=sp, lead=lead, co=co, st=st, gone=gone, out=out, prj=prj)


def test_schema_v2_objects(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("project_researchers", "submission_files", "file_chunks", "integrity_events", "notifications", "project_events", "profiles", "profile_likes"):
        assert t in tables
    cols = lambda t: {r["name"] for r in conn.execute(f"PRAGMA table_info({t})")}
    assert {"is_blacklisted", "blacklisted_at"} <= cols("users")
    assert "pending_skills" in cols("students")
    assert {"researcher_pct", "project_pct"} <= cols("problems")
    assert {"status", "joined_at", "removed_at", "removed_reason"} <= cols("project_members")
    assert "originality" in cols("work_submissions")
    idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_sf_project_path", "idx_notif_user_read", "idx_pe_project_created"} <= idx


def test_ledger_project_fund_allowed_and_checks(conn, world):
    conn.execute(
        "INSERT INTO ledger_entries(id, user_id, amount, type, created_at) VALUES(?,?,?,?,?)",
        (new_id(), world["sp"], 1.0, "project_fund", now()),
    )
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO ledger_entries(id, user_id, amount, type, created_at) VALUES(?,?,?,?,?)",
            (new_id(), world["sp"], 1.0, "bogus", now()),
        )
    with pytest.raises(Exception):
        conn.execute("UPDATE project_members SET status='nope' WHERE project_id=?", (world["prj"],))


def test_access_helpers_every_role(conn, world):
    w, prj = world, world["prj"]
    assert project_role(conn, prj, w["sp"]) == "sponsor"
    assert project_role(conn, prj, w["lead"]) == "lead"
    assert project_role(conn, prj, w["co"]) == "researcher"
    assert project_role(conn, prj, w["st"]) == "student"
    assert project_role(conn, prj, w["gone"]) is None  # removed student
    assert project_role(conn, prj, w["out"]) is None
    assert sponsor_id(conn, prj) == w["sp"] and lead_id(conn, prj) == w["lead"]
    assert researcher_ids(conn, prj) == [w["lead"], w["co"]]
    assert active_student_ids(conn, prj) == [w["st"]]
    assert is_project_researcher(conn, prj, w["co"]) and not is_project_researcher(conn, prj, w["st"])


def test_require_project_access(conn, world):
    w, prj = world, world["prj"]
    u = lambda uid, role: CurrentUser(id=uid, role=role, name="n", email="e")
    assert require_project_access(conn, prj, u(w["st"], "student")) == "student"
    assert require_project_access(conn, prj, u(w["lead"], "researcher"), {"lead", "researcher"}) == "lead"
    with pytest.raises(AppError) as e:
        require_project_access(conn, prj, u(w["st"], "student"), {"lead", "researcher"})
    assert e.value.status_code == 403
    with pytest.raises(AppError) as e:
        require_project_access(conn, prj, u(w["gone"], "student"))
    assert e.value.status_code == 403
    with pytest.raises(AppError) as e:
        require_project_access(conn, "missing", u(w["st"], "student"))
    assert e.value.status_code == 404


def test_notify_and_log_event(conn, world):
    st = world["st"]
    notify_many(conn, [st, st, None], "t", "Hello", link="/x")
    notify(conn, None, "t", "ignored")
    rows = conn.execute("SELECT * FROM notifications WHERE user_id=?", (st,)).fetchall()
    assert len(rows) == 1 and rows[0]["is_read"] == 0 and rows[0]["link"] == "/x"
    log_event(conn, world["prj"], None, "project_created", "m", ref_id="r", meta={"a": 1})
    ev = conn.execute("SELECT * FROM project_events WHERE project_id=?", (world["prj"],)).fetchone()
    assert ev["actor_id"] is None and ev["meta"] == '{"a": 1}'


@pytest.mark.parametrize("bad", ["../x", "a/../b", "/abs/p", "C:/x", "a//b", "", "a/", "x" * 301, "..\\x"])
def test_safe_path_rejects(bad):
    with pytest.raises(AppError) as e:
        storage.safe_path(bad)
    assert e.value.status_code == 422


def test_safe_path_normalises():
    assert storage.safe_path("src\\app\\main.py") == "src/app/main.py"
    assert storage.safe_path("./src/a.py") == "src/a.py"


def test_storage_roundtrip_and_text_detection(conn):
    sp = storage.save_file("proj1", "file1", b"hello")
    assert sp == "proj1/file1" and storage.read_file(sp) == b"hello"
    storage.delete_file(sp)
    with pytest.raises(AppError):
        storage.read_file(sp)
    storage.delete_file(sp)  # idempotent
    with pytest.raises(AppError):
        storage.read_file("../../etc/passwd")
    assert storage.is_text("a.py", b"print(1)") and storage.is_text("README", b"hi")
    assert not storage.is_text("a.png", b"hi") and not storage.is_text("a.py", b"a\x00b")
    assert not storage.is_text("a.txt", b"\xff\xfe\xfa")
    assert storage.decode_text(b"\xff\xfe") is None and storage.decode_text("é".encode()) == "é"
