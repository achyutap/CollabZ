from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.modules.files import service
from app.modules.files.schemas import BulkVisibilityBody, FileContent, FileOut, VisibilityBody

router = APIRouter()


@router.get("/projects/{project_id}/files", response_model=list[FileOut])
def list_files(project_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.project_tree(conn, project_id, user)


@router.get("/files/{file_id}/content", response_model=FileContent)
def file_content(file_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.content(conn, file_id, user)


@router.get("/files/{file_id}/download")
def file_download(file_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.download(conn, file_id, user)


@router.get("/files/{file_id}/versions", response_model=list[FileOut])
def file_versions(file_id: str, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.versions(conn, file_id, user)


@router.patch("/files/{file_id}/visibility", response_model=FileOut)
def set_visibility(file_id: str, body: VisibilityBody, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.set_visibility_one(conn, file_id, user, body.is_public)


@router.post("/projects/{project_id}/files/visibility", response_model=list[FileOut])
def set_visibility_bulk(project_id: str, body: BulkVisibilityBody, user: CurrentUser = Depends(get_current_user), conn=Depends(get_db)):
    return service.set_visibility_many(conn, project_id, user, body.file_ids, body.is_public)
