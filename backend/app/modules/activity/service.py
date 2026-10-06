import json

from app.core.access import require_project_access

DEFAULT_LIMIT = 100
MAX_LIMIT = 300


def _meta(raw) -> dict:
    try:
        v = json.loads(raw or "{}")
        return v if isinstance(v, dict) else {}
    except (TypeError, ValueError):
        return {}


def list_activity(conn, project_id: str, user, user_id: str | None, limit: int | None) -> list[dict]:
    require_project_access(conn, project_id, user)
    try:
        limit = int(limit) if limit is not None else DEFAULT_LIMIT
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))
    sql = (
        "SELECT e.*, u.name AS actor_name, u.role AS actor_role FROM project_events e "
        "LEFT JOIN users u ON u.id = e.actor_id WHERE e.project_id=?"
    )
    params: list = [project_id]
    if user_id:
        sql += " AND (e.actor_id=? OR json_extract(e.meta, '$.student_id')=?)"
        params += [user_id, user_id]
    sql += " ORDER BY e.created_at DESC, e.rowid DESC LIMIT ?"
    params.append(limit)
    out = []
    for r in conn.execute(sql, params).fetchall():
        actor = None
        if r["actor_id"] and r["actor_name"] is not None:
            actor = {"id": r["actor_id"], "name": r["actor_name"], "role": r["actor_role"]}
        out.append({
            "id": r["id"], "type": r["type"], "actor": actor, "message": r["message"],
            "ref_id": r["ref_id"], "meta": _meta(r["meta"]), "created_at": r["created_at"],
        })
    return out
