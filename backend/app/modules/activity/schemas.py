from pydantic import BaseModel


class Actor(BaseModel):
    id: str
    name: str
    role: str


class ActivityItem(BaseModel):
    id: str
    type: str
    actor: Actor | None
    message: str
    ref_id: str | None
    meta: dict
    created_at: str
