import sqlite3

from app.core.errors import AppError


def _n(conn, sql, params) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def list_notifications(conn: sqlite3.Connection, user_id: str, unread_only: bool) -> list:
    sql = "SELECT id, type, title, body, link, is_read, created_at FROM notifications WHERE user_id=?"
    if unread_only:
        sql += " AND is_read=0"
    sql += " ORDER BY created_at DESC, rowid DESC LIMIT 50"
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "title": r["title"],
            "body": r["body"],
            "link": r["link"],
            "is_read": bool(r["is_read"]),
            "created_at": r["created_at"],
        }
        for r in conn.execute(sql, (user_id,)).fetchall()
    ]


def mark_read(conn: sqlite3.Connection, user_id: str, notification_id: str) -> dict:
    cur = conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (notification_id, user_id))
    if cur.rowcount == 0:
        raise AppError(404, "NOT_FOUND", "Notification not found")
    return {"ok": True}


def mark_all_read(conn: sqlite3.Connection, user_id: str) -> dict:
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0", (user_id,))
    return {"ok": True}


def counts(conn: sqlite3.Connection, user_id: str, role: str) -> dict:
    requests = approvals = 0
    if role == "researcher":
        requests = _n(conn, "SELECT COUNT(*) FROM researcher_requests WHERE researcher_id=? AND status='pending'", (user_id,))
        approvals = _n(
            conn,
            "SELECT COUNT(*) FROM work_submissions ws JOIN projects p ON p.id=ws.project_id "
            "WHERE ws.status='pending' AND p.status='active' AND EXISTS("
            "SELECT 1 FROM project_researchers pr WHERE pr.project_id=p.id AND pr.researcher_id=?)",
            (user_id,),
        )
    elif role == "student":
        requests = _n(conn, "SELECT COUNT(*) FROM student_requests WHERE student_id=? AND status='pending'", (user_id,))
        approvals = _n(conn, "SELECT COUNT(*) FROM work_submissions WHERE student_id=? AND status='pending'", (user_id,))
    unread = _n(conn, "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user_id,))
    return {"requests": requests, "approvals": approvals, "notifications": unread}
