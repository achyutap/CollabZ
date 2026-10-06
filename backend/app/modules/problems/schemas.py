from typing import Optional

from pydantic import BaseModel, Field


class ProblemCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=30)
    budget: float = Field(gt=0)
    student_pct: int = Field(ge=0, le=100)
    researcher_pct: Optional[int] = Field(default=None, ge=0, le=100)
    project_pct: Optional[int] = Field(default=None, ge=0, le=100)


class SkillsPatch(BaseModel):
    required_skills: list[str]
