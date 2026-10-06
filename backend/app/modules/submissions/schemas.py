from typing import Optional

from pydantic import BaseModel


class ReviewBody(BaseModel):
    approve: bool
    feedback: Optional[str] = None
    public_file_ids: Optional[list[str]] = None


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


class IntegrityInfo(BaseModel):
    action: str
    message: str


class SubmissionOut(BaseModel):
    id: str
    project_id: str
    student_id: str
    student_name: str
    commit_msg: str
    description: Optional[str]
    status: str
    reviewer_feedback: Optional[str]
    ai_quality_score: Optional[float]
    created_at: str
    reviewed_at: Optional[str]
    files: list[FileOut]
    originality: str
    integrity: Optional[IntegrityInfo]
