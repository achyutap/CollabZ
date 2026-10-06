from pydantic import BaseModel


class StudentRequestCreate(BaseModel):
    student_id: str
    skill: str


class RespondBody(BaseModel):
    accept: bool
