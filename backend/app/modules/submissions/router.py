import json
from typing import Optional

from fastapi import APIRouter, Depends, Request

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.errors import AppError

from . import service
from .schemas import ReviewBody, SubmissionOut

router = APIRouter()


def _bad(msg):
    return AppError(422, "VALIDATION_ERROR", msg)


@router.post("/projects/{project_id}/submissions", response_model=SubmissionOut)
async def create_submission(
    project_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_db),
):
    ctype = (request.headers.get("content-type") or "").lower()
    files = []
    if ctype.startswith("multipart/form-data") or ctype.startswith("application/x-www-form-urlencoded"):
        try:
            form = await request.form()
        except Exception:
            raise _bad("Invalid form body")
        commit_msg = form.get("commit_msg")
        description = form.get("description")
        if not isinstance(description, str) or not description.strip():
            description = None
        uploads = [u for u in form.getlist("files") if hasattr(u, "filename") and hasattr(u, "read")]
        if len(uploads) > service.MAX_FILES:
            raise _bad(f"At most {service.MAX_FILES} files per submission")
        paths = []
        raw_paths = form.get("paths")
        if isinstance(raw_paths, str) and raw_paths.strip():
            try:
                paths = json.loads(raw_paths)
            except ValueError:
                raise _bad("paths must be a JSON array string")
            if not isinstance(paths, list):
                raise _bad("paths must be a JSON array string")
        for i, up in enumerate(uploads):
            data = await up.read(service.MAX_FILE_BYTES + 1)
            p = paths[i] if i < len(paths) else None
            if not isinstance(p, str) or not p.strip():
                p = up.filename or ""
            files.append((p, data))
    else:
        try:
            body = await request.json()
        except Exception:
            raise _bad("Invalid JSON body")
        if not isinstance(body, dict):
            raise _bad("Body must be an object")
        commit_msg, description = body.get("commit_msg"), body.get("description")
    return service.create_submission(conn, user, project_id, commit_msg, description, files)


@router.get("/projects/{project_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(
    project_id: str,
    student_id: Optional[str] = None,
    status: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_db),
):
    return service.list_submissions(conn, user, project_id, student_id, status)


@router.post("/submissions/{submission_id}/review", response_model=SubmissionOut)
def review_submission(
    submission_id: str,
    body: ReviewBody,
    user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_db),
):
    return service.review_submission(
        conn, user, submission_id, body.approve, body.feedback, body.public_file_ids
    )
