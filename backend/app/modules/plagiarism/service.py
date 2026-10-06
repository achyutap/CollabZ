from app.core.access import require_project_access


def project_integrity(conn, user, project_id):
    require_project_access(conn, project_id, user, {"lead", "researcher", "sponsor"})
    rows = conn.execute(
        "SELECT e.id, e.user_id AS student_id, u.name AS student_name, e.action, e.detail, e.created_at "
        "FROM integrity_events e JOIN users u ON u.id = e.user_id WHERE e.project_id=? "
        "ORDER BY e.created_at DESC, e.rowid DESC",
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def my_integrity(conn, user):
    rows = conn.execute(
        "SELECT id, action, detail, created_at FROM integrity_events WHERE user_id=? "
        "ORDER BY created_at DESC, rowid DESC",
        (user.id,),
    ).fetchall()
    return [dict(r) for r in rows]
