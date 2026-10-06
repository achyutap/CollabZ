from pydantic import BaseModel


class FileOut(BaseModel):
    id: str
    submission_id: str
    project_id: str
    path: str
    name: str
    size: int
    content_type: str
    is_text: bool
    version: int
    originality: str
    is_public: bool
    author_id: str
    author_name: str
    status: str
    created_at: str


class FileContent(BaseModel):
    id: str
    path: str
    size: int
    is_text: bool
    truncated: bool
    content: str | None


class VisibilityBody(BaseModel):
    is_public: bool


class BulkVisibilityBody(BaseModel):
    file_ids: list[str]
    is_public: bool
