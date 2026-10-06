import json
import sqlite3
from typing import Iterable, Optional

from app.core.db import new_id, now


def notify(conn: sqlite3.Connection, user_id: Optional[str], type: str, title: str, body: str = "", link: Optional[str] = None) -> None:
    if not user_id:
        return
    conn.execute(
        "INSERT INTO notifications(id, user_id, type, title, body, link, is_read, created_at) VALUES(?,?,?,?,?,?,0,?)",
        (new_id(), user_id, type, title, body or "", link, now()),
    )


def notify_many(conn: sqlite3.Connection, user_ids: Iterable[Optional[str]], type: str, title: str, body: str = "", link: Optional[str] = None) -> None:
    seen = set()
    for uid in user_ids:
        if uid and uid not in seen:
            seen.add(uid)
            notify(conn, uid, type, title, body, link)


def log_event(conn: sqlite3.Connection, project_id: str, actor_id: Optional[str], type: str, message: str, ref_id: Optional[str] = None, meta: Optional[dict] = None) -> None:
    conn.execute(
        "INSERT INTO project_events(id, project_id, actor_id, type, message, ref_id, meta, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (new_id(), project_id, actor_id, type, message, ref_id, json.dumps(meta or {}), now()),
    )
