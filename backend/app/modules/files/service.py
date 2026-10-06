import re
from urllib.parse import quote

from fastapi import Response

from app.core.access import project_role, require_project_access
from app.core.db import transaction
from app.core.errors import AppError
from app.core.notify import log_event, notify_many
from app.core.storage import decode_text, read_file

MAX_CONTENT = 512 * 1024
RESEARCHER_ROLES = {"lead", "researcher"}

BASE = (
    "SELECT f.*, u.name AS author_name, s.status AS sub_status "
    "FROM submission_files f JOIN users u ON u.id = f.author_id "
    "JOIN work_submissions s ON s.id = f.submission_id "
)


def to_out(r) -> dict:
    return {
        "id": r["id"], "submission_id": r["submission_id"], "project_id": r["project_id"],
        "path": r["path"], "name": r["name"], "size": r["size"], "content_type": r["content_type"],
        "is_text": bool(r["is_text"]), "version": r["version"], "originality": r["originality"],
        "is_public": bool(r["is_public"]), "author_id": r["author_id"], "author_name": r["author_name"],
        "status": r["sub_status"], "created_at": r["created_at"],
    }


def _get_file(conn, file_id: str):
    r = conn.execute(BASE + "WHERE f.id=?", (file_id,)).fetchone()
    if r is None:
        raise AppError(404, "NOT_FOUND", "File not found")
    return r


def _access(conn, f, user) -> str | None:
    """Return the project role, or None for a public-file visitor. Raises 403 otherwise."""
    role = project_role(conn, f["project_id"], user.id)
    if role is None and not f["is_public"]:
        raise AppError(403, "FORBIDDEN", "You do not have access to this file")
    return role


def project_tree(conn, project_id: str, user) -> list[dict]:
    require_project_access(conn, project_id, user)
    rows = conn.execute(
        BASE + "WHERE f.project_id=? AND s.status != 'rejected' ORDER BY f.path ASC, f.version DESC, f.created_at DESC",
        (project_id,),
    ).fetchall()
    seen, out = set(), []
    for r in rows:
        if r["path"] in seen:
            continue
        seen.add(r["path"])
        out.append(to_out(r))
    return out


def content(conn, file_id: str, user) -> dict:
    f = _get_file(conn, file_id)
    _access(conn, f, user)
    text, truncated = None, False
    if f["is_text"]:
        data = read_file(f["storage_path"])
        truncated = len(data) > MAX_CONTENT
        chunk = data[:MAX_CONTENT]
        for cut in range(0, 4):  # avoid splitting a multi-byte character
            text = decode_text(chunk[: len(chunk) - cut] if cut else chunk)
            if text is not None:
                break
        if text is None:
            truncated = False
    return {"id": f["id"], "path": f["path"], "size": f["size"], "is_text": bool(f["is_text"]), "truncated": truncated, "content": text}


def download(conn, file_id: str, user) -> Response:
    f = _get_file(conn, file_id)
    _access(conn, f, user)
    data = read_file(f["storage_path"])
    ascii_name = re.sub(r'[^A-Za-z0-9._ -]', "_", f["name"]) or "file"
    disp = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(f['name'])}"
    return Response(content=data, media_type=f["content_type"] or "application/octet-stream", headers={"Content-Disposition": disp})


def versions(conn, file_id: str, user) -> list[dict]:
    f = _get_file(conn, file_id)
    role = _access(conn, f, user)
    rows = conn.execute(
        BASE + "WHERE f.project_id=? AND f.path=? ORDER BY f.version DESC, f.created_at DESC",
        (f["project_id"], f["path"]),
    ).fetchall()
    if role is None:
        rows = [r for r in rows if r["is_public"]]
    return [to_out(r) for r in rows]


def _apply(conn, project_id: str, user, ids: list[str], is_public: bool) -> list[dict]:
    require_project_access(conn, project_id, user, RESEARCHER_ROLES)
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise AppError(422, "VALIDATION_ERROR", "file_ids must not be empty")
    marks = ",".join("?" * len(ids))
    rows = conn.execute(BASE + f"WHERE f.id IN ({marks})", ids).fetchall()
    by_id = {r["id"]: r for r in rows}
    for fid in ids:
        r = by_id.get(fid)
        if r is None or r["project_id"] != project_id:
            raise AppError(404, "NOT_FOUND", "File not found in this project")
        if is_public and (r["sub_status"] != "approved" or r["originality"] != "original"):
            raise AppError(400, "BAD_STATE", "Only approved, original files can be made public")
    changed = [fid for fid in ids if bool(by_id[fid]["is_public"]) != is_public]
    with transaction(conn):
        if changed:
            m2 = ",".join("?" * len(changed))
            conn.execute(f"UPDATE submission_files SET is_public=? WHERE id IN ({m2})", [1 if is_public else 0, *changed])
            verb = "published" if is_public else "unpublished"
            log_event(
                conn, project_id, user.id, "files_published" if is_public else "files_unpublished",
                f"{user.name} {verb} {len(changed)} file(s)", None, {"file_ids": changed, "count": len(changed)},
            )
            if is_public:
                authors = {by_id[fid]["author_id"] for fid in changed} - {user.id}
                notify_many(
                    conn, sorted(authors), "files_published", "Your files are now public",
                    f"{user.name} published {len(changed)} file(s) from your work.", f"/projects/{project_id}?tab=files",
                )
    refreshed = conn.execute(BASE + f"WHERE f.id IN ({marks})", ids).fetchall()
    order = {fid: i for i, fid in enumerate(ids)}
    return [to_out(r) for r in sorted(refreshed, key=lambda r: order[r["id"]])]


def set_visibility_one(conn, file_id: str, user, is_public: bool) -> dict:
    f = _get_file(conn, file_id)
    return _apply(conn, f["project_id"], user, [file_id], is_public)[0]


def set_visibility_many(conn, project_id: str, user, file_ids: list[str], is_public: bool) -> list[dict]:
    return _apply(conn, project_id, user, file_ids, is_public)
