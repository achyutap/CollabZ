import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, role TEXT NOT NULL CHECK(role IN('sponsor','researcher','student')), name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL, is_blacklisted INTEGER NOT NULL DEFAULT 0, blacklisted_at TEXT);
CREATE TABLE IF NOT EXISTS researchers(user_id TEXT PRIMARY KEY REFERENCES users(id), skills TEXT NOT NULL DEFAULT '[]', rating REAL NOT NULL DEFAULT 3.0, bio TEXT NOT NULL DEFAULT '', availability REAL NOT NULL DEFAULT 1.0);
CREATE TABLE IF NOT EXISTS students(user_id TEXT PRIMARY KEY REFERENCES users(id), skills TEXT NOT NULL DEFAULT '[]', temp_rating REAL, final_rating REAL, projects_done INTEGER NOT NULL DEFAULT 0, last_active_at TEXT NOT NULL, pending_skills TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS problems(id TEXT PRIMARY KEY, sponsor_id TEXT NOT NULL REFERENCES users(id), title TEXT NOT NULL, description TEXT NOT NULL, budget REAL NOT NULL, student_pct INTEGER NOT NULL CHECK(student_pct BETWEEN 0 AND 100), required_skills TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL, researcher_pct INTEGER NOT NULL DEFAULT 70, project_pct INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS researcher_requests(id TEXT PRIMARY KEY, problem_id TEXT NOT NULL REFERENCES problems(id), researcher_id TEXT NOT NULL REFERENCES users(id), match_score REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, UNIQUE(problem_id, researcher_id));
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, problem_id TEXT NOT NULL UNIQUE REFERENCES problems(id), researcher_id TEXT NOT NULL REFERENCES users(id), status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL, completed_at TEXT);
CREATE TABLE IF NOT EXISTS skill_needs(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), skill TEXT NOT NULL, count INTEGER NOT NULL CHECK(count BETWEEN 1 AND 10), UNIQUE(project_id, skill));
CREATE TABLE IF NOT EXISTS student_requests(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), student_id TEXT NOT NULL REFERENCES users(id), skill TEXT NOT NULL, match_score REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, UNIQUE(project_id, student_id, skill));
CREATE TABLE IF NOT EXISTS project_members(project_id TEXT NOT NULL REFERENCES projects(id), student_id TEXT NOT NULL REFERENCES users(id), skill TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active','removed','blacklisted')), joined_at TEXT, removed_at TEXT, removed_reason TEXT, PRIMARY KEY(project_id, student_id));
CREATE TABLE IF NOT EXISTS work_submissions(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), student_id TEXT NOT NULL REFERENCES users(id), commit_msg TEXT NOT NULL, description TEXT, status TEXT NOT NULL DEFAULT 'pending', ai_quality_score REAL, reviewer_feedback TEXT, created_at TEXT NOT NULL, reviewed_at TEXT, originality TEXT NOT NULL DEFAULT 'original' CHECK(originality IN('original','copied')));
CREATE TABLE IF NOT EXISTS rewards(project_id TEXT NOT NULL REFERENCES projects(id), student_id TEXT NOT NULL REFERENCES users(id), share_pct REAL NOT NULL, amount REAL NOT NULL, PRIMARY KEY(project_id, student_id));
CREATE TABLE IF NOT EXISTS project_ratings(project_id TEXT NOT NULL REFERENCES projects(id), student_id TEXT NOT NULL REFERENCES users(id), score REAL NOT NULL, PRIMARY KEY(project_id, student_id));
CREATE TABLE IF NOT EXISTS quiz_questions(id TEXT PRIMARY KEY, skill TEXT NOT NULL, question TEXT NOT NULL, options TEXT NOT NULL, answer_index INTEGER NOT NULL, UNIQUE(skill, question));
CREATE TABLE IF NOT EXISTS quiz_attempts(id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES users(id), skills TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, project_id TEXT, user_id TEXT NOT NULL REFERENCES users(id), filename TEXT NOT NULL, text TEXT NOT NULL, plagiarism_score REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS document_chunks(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), chunk_text TEXT NOT NULL, embedding TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chat_messages(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), user_id TEXT NOT NULL REFERENCES users(id), role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS wallets(user_id TEXT PRIMARY KEY REFERENCES users(id), balance REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS ledger_entries(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), problem_id TEXT, project_id TEXT, amount REAL NOT NULL, type TEXT NOT NULL CHECK(type IN('escrow','payout','refund','seed','project_fund')), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_researchers(project_id TEXT NOT NULL REFERENCES projects(id), researcher_id TEXT NOT NULL REFERENCES users(id), role TEXT NOT NULL CHECK(role IN('lead','researcher')), share_pct REAL, joined_at TEXT NOT NULL, PRIMARY KEY(project_id, researcher_id));
CREATE TABLE IF NOT EXISTS submission_files(id TEXT PRIMARY KEY, submission_id TEXT NOT NULL REFERENCES work_submissions(id), project_id TEXT NOT NULL REFERENCES projects(id), author_id TEXT NOT NULL REFERENCES users(id), path TEXT NOT NULL, name TEXT NOT NULL, size INTEGER NOT NULL, content_type TEXT NOT NULL, is_text INTEGER NOT NULL, storage_path TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, originality TEXT NOT NULL DEFAULT 'original', is_public INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS file_chunks(id TEXT PRIMARY KEY, file_id TEXT NOT NULL REFERENCES submission_files(id), user_id TEXT NOT NULL, project_id TEXT NOT NULL, chunk_text TEXT NOT NULL, embedding TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS integrity_events(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), project_id TEXT, submission_id TEXT, action TEXT NOT NULL CHECK(action IN('warned','blocked')), detail TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), type TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', link TEXT, is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_events(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), actor_id TEXT, type TEXT NOT NULL, message TEXT NOT NULL, ref_id TEXT, meta TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profiles(user_id TEXT PRIMARY KEY REFERENCES users(id), headline TEXT NOT NULL DEFAULT '', about TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '', links TEXT NOT NULL DEFAULT '{}', details TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profile_likes(liker_id TEXT NOT NULL REFERENCES users(id), user_id TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, PRIMARY KEY(liker_id, user_id));
CREATE INDEX IF NOT EXISTS idx_problems_sponsor ON problems(sponsor_id);
CREATE INDEX IF NOT EXISTS idx_rr_problem ON researcher_requests(problem_id);
CREATE INDEX IF NOT EXISTS idx_rr_researcher ON researcher_requests(researcher_id);
CREATE INDEX IF NOT EXISTS idx_projects_researcher ON projects(researcher_id);
CREATE INDEX IF NOT EXISTS idx_skill_needs_project ON skill_needs(project_id);
CREATE INDEX IF NOT EXISTS idx_sr_project ON student_requests(project_id);
CREATE INDEX IF NOT EXISTS idx_sr_student ON student_requests(student_id);
CREATE INDEX IF NOT EXISTS idx_members_student ON project_members(student_id);
CREATE INDEX IF NOT EXISTS idx_ws_project ON work_submissions(project_id);
CREATE INDEX IF NOT EXISTS idx_ws_student ON work_submissions(student_id);
CREATE INDEX IF NOT EXISTS idx_rewards_student ON rewards(student_id);
CREATE INDEX IF NOT EXISTS idx_pr_student ON project_ratings(student_id);
CREATE INDEX IF NOT EXISTS idx_qa_student ON quiz_attempts(student_id);
CREATE INDEX IF NOT EXISTS idx_docs_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chat_project ON chat_messages(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_ledger_user ON ledger_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_pres_researcher ON project_researchers(researcher_id);
CREATE INDEX IF NOT EXISTS idx_sf_submission ON submission_files(submission_id);
CREATE INDEX IF NOT EXISTS idx_sf_project ON submission_files(project_id);
CREATE INDEX IF NOT EXISTS idx_sf_author ON submission_files(author_id);
CREATE INDEX IF NOT EXISTS idx_sf_project_path ON submission_files(project_id, path);
CREATE INDEX IF NOT EXISTS idx_fc_file ON file_chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_ie_user ON integrity_events(user_id);
CREATE INDEX IF NOT EXISTS idx_ie_project ON integrity_events(project_id);
CREATE INDEX IF NOT EXISTS idx_ie_submission ON integrity_events(submission_id);
CREATE INDEX IF NOT EXISTS idx_notif_user_read ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_pe_project_created ON project_events(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_pl_user ON profile_likes(user_id);
"""


def _db_path() -> str:
    return os.environ.get("DB_PATH") or settings.db_path


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()
