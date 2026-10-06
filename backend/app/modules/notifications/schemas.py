from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    body: str
    link: Optional[str]
    is_read: bool
    created_at: str


class CountsOut(BaseModel):
    requests: int
    approvals: int
    notifications: int


class OkOut(BaseModel):
    ok: bool = True
