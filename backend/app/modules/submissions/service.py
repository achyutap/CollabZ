import io
import mimetypes
import re
from typing import Optional

from app.core.access import require_project_access, researcher_ids, sponsor_id
from app.core.db import new_id, now, transaction
from app.core.embeddings import chunk_text, cosine, embed_texts
from app.core.errors import AppError
from app.core.llm import LLMUnavailable, complete_json
from app.core.notify import log_event, notify, notify_many
from app.core.storage import decode_text, delete_file, is_text, safe_path, save_file

import json

DUPLICATE_THRESHOLD = 0.9
COPY_CHUNK_THRESHOLD = 0.9
COPIED_RATIO = 0.5
MIN_WORDS = 40
MAX_FILES = 30
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 25 * 1024 * 1024
STATUSES = ("pending", "approved", "rejected")
RESEARCHER_ROLES = {"lead", "researcher"}

WARN_MESSAGE = (
    "Plagiarism warning: this submission looks copied. This is your first warning. "
    "A second incident will block your account."
)
BLOCK_MESSAGE = "Your account has been blocked and removed from all projects for repeated plagiarism."

SYSTEM_PROMPT = (
    "Rate this work-log message 0-1 for specificity, concrete deliverable, technical substance; "
    "vague or padded messages (e.g. 'fixed stuff') < 0.2; a clear feature saying what/where/how 0.7-1.0. "
    'Return JSON {"score": number, "reason": string}'
)

TECHNICAL_KEYWORDS = {
    "api", "endpoint", "database", "model", "component", "test", "auth", "deploy", "query",
    "algorithm", "sensor", "ui", "function", "class", "bug", "schema", "validation", "optimize",
    "backend", "frontend", "migration", "cache", "index", "route", "parser",
}


def _validation(msg):
    return AppError(422, "VALIDATION_ERROR", msg)


# ---------------------------------------------------------------- quality scoring
def heuristic_quality(text: str) -> float:
    words = text.split()
    tokens = set(re.findall(r"[a-z0-9_]+", text.lower()))
    kw = len(tokens & TECHNICAL_KEYWORDS)
    return round(min(1.0, 0.15 + 0.012 * len(words) + 0.1 * kw), 2)


def score_quality(commit_msg: str, description: Optional[str] = None) -> float:
    text = commit_msg.strip()
    if description and description.strip():
        text += "\n" + description.strip()
    try:
        data = complete_json(SYSTEM_PROMPT, text)
        val = float(data["score"])
        if val != val:
            raise ValueError("nan")
        return round(min(1.0, max(0.0, val)), 2)
    except (LLMUnavailable, KeyError, TypeError, ValueError):
        return heuristic_quality(text)


# ---------------------------------------------------------------- output builders
def _file_out(r) -> dict:
    return {
        "id": r["id"], "submission_id": r["submission_id"], "project_id": r["project_id"],
        "path": r["path"], "name": r["name"], "size": r["size"], "content_type": r["content_type"],
        "is_text": bool(r["is_text"]), "version": r["version"], "originality": r["originality"],
        "is_public": bool(r["is_public"]), "author_id": r["author_id"], "author_name": r["author_name"],
        "status": r["submission_status"], "created_at": r["created_at"],
    }


def _files_for(conn, submission_ids) -> dict:
    out = {sid: [] for sid in submission_ids}
    ids = list(submission_ids)
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        q = ",".join("?" * len(part))
        rows = conn.execute(
            "SELECT f.*, u.name AS author_name, s.status AS submission_status FROM submission_files f "
            "JOIN users u ON u.id = f.author_id JOIN work_submissions s ON s.id = f.submission_id "
            f"WHERE f.submission_id IN ({q}) ORDER BY f.path, f.version",
            part,
        ).fetchall()
        for r in rows:
            out[r["submission_id"]].append(_file_out(r))
    return out


def _out(row, files, show_score: bool, integrity=None) -> dict:
    return {
        "id": row["id"], "project_id": row["project_id"], "student_id": row["student_id"],
        "student_name": row["student_name"], "commit_msg": row["commit_msg"],
        "description": row["description"], "status": row["status"],
        "reviewer_feedback": row["reviewer_feedback"],
        "ai_quality_score": row["ai_quality_score"] if show_score else None,
        "created_at": row["created_at"], "reviewed_at": row["reviewed_at"],
        "files": files, "originality": row["originality"], "integrity": integrity,
    }


def _fetch(conn, submission_id):
    return conn.execute(
        "SELECT s.*, u.name AS student_name FROM work_submissions s JOIN users u ON u.id = s.student_id "
        "WHERE s.id=?", (submission_id,)
    ).fetchone()


# ---------------------------------------------------------------- originality
def _extract_text(name: str, data: bytes, text_flag: bool) -> Optional[str]:
    low = name.lower()
    try:
        if low.endswith(".pdf"):
            from pypdf import PdfReader

            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        elif low.endswith(".docx"):
            import docx

            text = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
        elif text_flag:
            text = decode_text(data)
        else:
            return None
    except Exception:
        return None
    if not text:
        return None
    return " ".join(text.split()) or None


def _other_vectors(conn, user_id, project_id):
    """Chunks of OTHER users in OTHER projects, plus the document corpus of other users."""
    import json as _json

    vecs = [
        _json.loads(r["embedding"])
        for r in conn.execute(
            "SELECT embedding FROM file_chunks WHERE user_id != ? AND project_id != ?", (user_id, project_id)
        ).fetchall()
    ]
    vecs += [
        _json.loads(r["embedding"])
        for r in conn.execute(
            "SELECT c.embedding FROM document_chunks c JOIN documents d ON d.id = c.document_id "
            "WHERE d.user_id != ?", (user_id,)
        ).fetchall()
    ]
    return vecs


def _prepare_files(conn, user_id, project_id, files):
    prepared, others = [], None
    for path, data in files:
        name = path.rsplit("/", 1)[-1]
        txt_flag = is_text(name, data)
        text = _extract_text(name, data, txt_flag)
        chunks, vecs, originality = [], [], "original"
        if text and len(text.split()) >= MIN_WORDS:
            chunks = chunk_text(text, 200, 40)
            vecs = embed_texts(chunks)
            if others is None:
                others = _other_vectors(conn, user_id, project_id)
            flagged = sum(1 for v in vecs if any(cosine(v, o) >= COPY_CHUNK_THRESHOLD for o in others))
            if chunks and flagged / len(chunks) >= COPIED_RATIO:
                originality = "copied"
        prepared.append({
            "path": path, "name": name, "data": data,
            "content_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
            "is_text": 1 if txt_flag else 0, "chunks": chunks, "vecs": vecs, "originality": originality,
        })
    return prepared


# ---------------------------------------------------------------- create
def _validate_input(commit_msg, description, files):
    if not isinstance(commit_msg, str) or not (10 <= len(commit_msg) <= 280):
        raise _validation("commit_msg must be 10-280 characters")
    if description is not None and not isinstance(description, str):
        raise _validation("description must be a string")
    if len(files) > MAX_FILES:
        raise _validation(f"At most {MAX_FILES} files per submission")
    total = 0
    cleaned = []
    for raw_path, data in files:
        if len(data) > MAX_FILE_BYTES:
            raise _validation("Each file must be at most 5MB")
        total += len(data)
        cleaned.append((safe_path(raw_path), data))
    if total > MAX_TOTAL_BYTES:
        raise _validation("Total upload must be at most 25MB")
    return cleaned


def _block_user(conn, user, project_id, detail):
    ts = now()
    with transaction(conn):
        pids = [
            r["project_id"]
            for r in conn.execute(
                "SELECT project_id FROM project_members WHERE student_id=? AND status='active'", (user.id,)
            ).fetchall()
        ]
        if project_id not in pids:
            pids.append(project_id)
        conn.execute("UPDATE users SET is_blacklisted=1, blacklisted_at=? WHERE id=?", (ts, user.id))
        conn.execute(
            "UPDATE project_members SET status='blacklisted', removed_at=?, removed_reason='blacklisted' "
            "WHERE student_id=? AND status='active'", (ts, user.id),
        )
        conn.execute(
            "UPDATE student_requests SET status='expired' WHERE student_id=? AND status='pending'", (user.id,)
        )
        conn.execute(
            "INSERT INTO integrity_events(id, user_id, project_id, submission_id, action, detail, created_at) "
            "VALUES(?,?,?,NULL,'blocked',?,?)", (new_id(), user.id, project_id, detail, ts),
        )
        notify(conn, user.id, "integrity_blocked", "Account blocked", BLOCK_MESSAGE, None)
        for pid in pids:
            notify_many(
                conn, researcher_ids(conn, pid) + [sponsor_id(conn, pid)], "integrity_alert",
                "Student blocked for plagiarism", f"{user.name} was blocked for repeated plagiarism and removed "
                "from this project.", f"/projects/{pid}?tab=work",
            )
    raise AppError(403, "BLACKLISTED", BLOCK_MESSAGE)


def create_submission(conn, user, project_id, commit_msg, description, files):
    """files: list of (relative_path, bytes)."""
    require_project_access(conn, project_id, user, {"student"})
    files = _validate_input(commit_msg, description, files)
    project = conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()
    if project["status"] != "active":
        raise AppError(400, "BAD_STATE", "Project is not active")

    earlier = [
        r["commit_msg"]
        for r in conn.execute(
            "SELECT commit_msg FROM work_submissions WHERE project_id=? AND student_id=?", (project_id, user.id)
        ).fetchall()
    ]
    if earlier:
        vecs = embed_texts([commit_msg] + earlier)
        if max(cosine(vecs[0], v) for v in vecs[1:]) > DUPLICATE_THRESHOLD:
            raise AppError(409, "DUPLICATE_SUBMISSION", "This looks like a duplicate of an earlier submission")

    score = score_quality(commit_msg, description)
    prepared = _prepare_files(conn, user.id, project_id, files)
    copied = any(p["originality"] == "copied" for p in prepared)
    prior = conn.execute("SELECT COUNT(*) AS n FROM integrity_events WHERE user_id=?", (user.id,)).fetchone()["n"]
    copied_names = ", ".join(p["path"] for p in prepared if p["originality"] == "copied")

    if copied and prior >= 1:
        # Nothing of this upload has been written to disk or DB yet, so nothing needs deleting.
        _block_user(conn, user, project_id, f"Repeated plagiarism detected in: {copied_names}")

    sid, ts = new_id(), now()
    link = f"/projects/{project_id}?tab=work"
    saved = []
    try:
        with transaction(conn):
            conn.execute(
                "INSERT INTO work_submissions(id, project_id, student_id, commit_msg, description, status, "
                "ai_quality_score, reviewer_feedback, created_at, reviewed_at, originality) "
                "VALUES(?,?,?,?,?,'pending',?,NULL,?,NULL,?)",
                (sid, project_id, user.id, commit_msg, description, score, ts,
                 "copied" if copied else "original"),
            )
            for p in prepared:
                fid = new_id()
                version = conn.execute(
                    "SELECT COALESCE(MAX(version), 0) AS v FROM submission_files WHERE project_id=? AND path=?",
                    (project_id, p["path"]),
                ).fetchone()["v"] + 1
                storage_path = save_file(project_id, fid, p["data"])
                saved.append(storage_path)
                conn.execute(
                    "INSERT INTO submission_files(id, submission_id, project_id, author_id, path, name, size, "
                    "content_type, is_text, storage_path, version, originality, is_public, created_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0,?)",
                    (fid, sid, project_id, user.id, p["path"], p["name"], len(p["data"]), p["content_type"],
                     p["is_text"], storage_path, version, p["originality"], ts),
                )
                for c, v in zip(p["chunks"], p["vecs"]):
                    conn.execute(
                        "INSERT INTO file_chunks(id, file_id, user_id, project_id, chunk_text, embedding) "
                        "VALUES(?,?,?,?,?,?)", (new_id(), fid, user.id, project_id, c, json.dumps(v)),
                    )
            integrity = {"action": "none", "message": ""}
            if copied:
                integrity = {"action": "warned", "message": WARN_MESSAGE}
                conn.execute(
                    "INSERT INTO integrity_events(id, user_id, project_id, submission_id, action, detail, "
                    "created_at) VALUES(?,?,?,?,'warned',?,?)",
                    (new_id(), user.id, project_id, sid, f"Copied files: {copied_names}", ts),
                )
                notify(conn, user.id, "integrity_warning", "Plagiarism warning", WARN_MESSAGE, link)
                notify_many(
                    conn, researcher_ids(conn, project_id) + [sponsor_id(conn, project_id)], "integrity_alert",
                    "Possible plagiarism", f"{user.name} submitted work that looks copied ({copied_names}).", link,
                )
            notify_many(
                conn, researcher_ids(conn, project_id), "submission_pending", "New submission to review",
                f"{user.name}: {commit_msg}", link,
            )
            log_event(
                conn, project_id, user.id, "submission_created", f"{user.name} submitted: {commit_msg}", sid,
                {"submission_id": sid, "student_id": user.id, "commit_msg": commit_msg,
                 "file_count": len(prepared), "status": "pending"},
            )
    except Exception:
        for s in saved:
            try:
                delete_file(s)
            except Exception:
                pass
        raise
    return _out(_fetch(conn, sid), _files_for(conn, [sid])[sid], show_score=False, integrity=integrity)


# ---------------------------------------------------------------- list
def list_submissions(conn, user, project_id, student_id=None, status=None):
    role = require_project_access(conn, project_id, user)
    if status is not None and status not in STATUSES:
        raise _validation("Invalid status filter")
    sql = (
        "SELECT s.*, u.name AS student_name FROM work_submissions s JOIN users u ON u.id = s.student_id "
        "WHERE s.project_id=?"
    )
    params = [project_id]
    if student_id:
        sql += " AND s.student_id=?"
        params.append(student_id)
    if status:
        sql += " AND s.status=?"
        params.append(status)
    sql += " ORDER BY s.created_at DESC, s.rowid DESC"
    rows = conn.execute(sql, params).fetchall()
    files = _files_for(conn, [r["id"] for r in rows])
    show = role in RESEARCHER_ROLES
    return [_out(r, files[r["id"]], show_score=show) for r in rows]


# ---------------------------------------------------------------- review
def review_submission(conn, user, submission_id, approve, feedback, public_file_ids):
    sub = conn.execute("SELECT project_id FROM work_submissions WHERE id=?", (submission_id,)).fetchone()
    if sub is None:
        raise AppError(404, "NOT_FOUND", "Submission not found")
    project_id = sub["project_id"]
    require_project_access(conn, project_id, user, RESEARCHER_ROLES)
    public_ids = list(dict.fromkeys(public_file_ids or []))
    with transaction(conn):
        sub = conn.execute("SELECT * FROM work_submissions WHERE id=?", (submission_id,)).fetchone()
        if sub["status"] != "pending":
            raise AppError(409, "CONFLICT", "Submission has already been reviewed")
        if public_ids:
            if not approve:
                raise AppError(400, "BAD_STATE", "Files can only be made public when approving")
            for fid in public_ids:
                f = conn.execute(
                    "SELECT originality FROM submission_files WHERE id=? AND submission_id=?", (fid, submission_id)
                ).fetchone()
                if f is None or f["originality"] != "original":
                    raise AppError(400, "BAD_STATE", "public_file_ids must be original files of this submission")
        ts = now()
        score = sub["ai_quality_score"]
        if score is None:
            score = score_quality(sub["commit_msg"], sub["description"])
        new_status = "approved" if approve else "rejected"
        conn.execute(
            "UPDATE work_submissions SET status=?, reviewer_feedback=?, reviewed_at=?, ai_quality_score=? WHERE id=?",
            (new_status, feedback, ts, score, submission_id),
        )
        file_count = conn.execute(
            "SELECT COUNT(*) AS n FROM submission_files WHERE submission_id=?", (submission_id,)
        ).fetchone()["n"]
        meta = {"submission_id": submission_id, "student_id": sub["student_id"], "commit_msg": sub["commit_msg"],
                "file_count": file_count, "status": new_status}
        for fid in public_ids:
            conn.execute("UPDATE submission_files SET is_public=1 WHERE id=?", (fid,))
        if public_ids:
            log_event(conn, project_id, user.id, "files_published",
                      f"{user.name} published {len(public_ids)} file(s)", submission_id,
                      {"submission_id": submission_id, "file_ids": public_ids})
        notify(conn, sub["student_id"], f"submission_{new_status}", f"Submission {new_status}",
               feedback or sub["commit_msg"], f"/projects/{project_id}?tab=work")
        log_event(conn, project_id, user.id, f"submission_{new_status}",
                  f"{user.name} {new_status} a submission: {sub['commit_msg']}", submission_id, meta)
    return _out(_fetch(conn, submission_id), _files_for(conn, [submission_id])[submission_id], show_score=True)
