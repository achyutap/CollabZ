from pydantic import BaseModel


class ProjectIntegrityItem(BaseModel):
    id: str
    student_id: str
    student_name: str
    action: str
    detail: str
    created_at: str


class MyIntegrityItem(BaseModel):
    id: str
    action: str
    detail: str
    created_at: str
