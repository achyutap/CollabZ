from pydantic import BaseModel, Field


class SkillNeedIn(BaseModel):
    skill: str
    count: int = Field(ge=1, le=10)


class ShareIn(BaseModel):
    researcher_id: str
    share_pct: float = Field(ge=0, le=100)
