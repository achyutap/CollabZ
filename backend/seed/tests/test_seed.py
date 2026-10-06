import json
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "seed_test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["LLM_MOCK"] = "true"

from app.core.db import get_conn  # noqa: E402
from seed.seed import run  # noqa: E402

TABLES = ["users", "wallets", "ledger_entries", "problems", "projects", "project_researchers", "project_members", "work_submissions",
          "submission_files", "file_chunks", "project_events", "notifications", "profiles", "profile_likes", "integrity_events",
          "quiz_questions", "quiz_attempts", "documents", "document_chunks", "rewards", "project_ratings", "student_requests", "skill_needs"]


def counts(conn):
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}


def test_seed_idempotent_and_consistent():
    run()
    conn = get_conn()
    first = counts(conn)
    run()
    assert counts(conn) == first

    assert first["users"] == 31 and first["quiz_questions"] == 72 and first["quiz_attempts"] == 20
    assert first["documents"] == 1 and first["document_chunks"] >= 2
    uid = lambda e: conn.execute("SELECT id FROM users WHERE email=?", (e,)).fetchone()[0]

    # wallets / ledger
    assert conn.execute("SELECT balance FROM wallets WHERE user_id=?", (uid("sponsor1@demo.com"),)).fetchone()[0] == 400000
    for r in conn.execute("SELECT w.user_id, w.balance, COALESCE((SELECT SUM(amount) FROM ledger_entries l WHERE l.user_id = w.user_id), 0) AS s FROM wallets w"):
        assert abs(r["balance"] - r["s"]) < 0.01, r["user_id"]

    # open demo problem
    p = conn.execute("SELECT * FROM problems WHERE title='Water quality monitoring using IoT'").fetchone()
    assert p["status"] == "open" and (p["student_pct"], p["researcher_pct"], p["project_pct"]) == (30, 60, 10)
    assert json.loads(p["required_skills"]) == ["iot", "python", "embedded_c", "data_analysis"]

    # completed project: rewards + payouts add up to the budget, 2 public files
    done = conn.execute("SELECT pr.* FROM projects pr WHERE status='completed'").fetchone()
    prob = conn.execute("SELECT * FROM problems WHERE id=?", (done["problem_id"],)).fetchone()
    paid = conn.execute("SELECT COALESCE(SUM(amount),0) FROM ledger_entries WHERE project_id=? AND type IN ('payout','project_fund','refund')", (done["id"],)).fetchone()[0]
    assert abs(paid - prob["budget"]) < 0.01
    assert abs(conn.execute("SELECT SUM(share_pct) FROM rewards WHERE project_id=?", (done["id"],)).fetchone()[0] - 100) < 0.05
    assert conn.execute("SELECT COUNT(*) FROM project_researchers WHERE project_id=?", (done["id"],)).fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM submission_files WHERE project_id=? AND is_public=1", (done["id"],)).fetchone()[0] == 2

    # active project
    act = conn.execute("SELECT * FROM projects WHERE status='active'").fetchone()
    stat = {r["status"]: r["c"] for r in conn.execute("SELECT status, COUNT(*) AS c FROM project_members WHERE project_id=? GROUP BY status", (act["id"],))}
    assert stat == {"active": 4, "removed": 1, "blacklisted": 1}
    assert conn.execute("SELECT COUNT(*) FROM submission_files WHERE project_id=? AND is_public=1", (act["id"],)).fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM work_submissions WHERE project_id=?", (act["id"],)).fetchone()[0] == 11
    assert conn.execute("SELECT COUNT(*) FROM project_researchers WHERE project_id=?", (act["id"],)).fetchone()[0] == 2

    # special students
    assert json.loads(conn.execute("SELECT pending_skills FROM students WHERE user_id=?", (uid("student10@demo.com"),)).fetchone()[0]) == ["ml"]
    assert conn.execute("SELECT COUNT(*) FROM integrity_events WHERE user_id=? AND action='warned'", (uid("student19@demo.com"),)).fetchone()[0] == 1
    assert conn.execute("SELECT is_blacklisted FROM users WHERE email='student20@demo.com'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 5
    assert os.path.exists(os.path.join(os.path.dirname(__file__), "..", "demo_corpus.txt"))
    conn.close()
