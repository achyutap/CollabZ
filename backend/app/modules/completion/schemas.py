from typing import Optional

from pydantic import BaseModel


class PayoutResearcher(BaseModel):
    researcher_id: str
    name: str
    role: str
    share_pct: float
    amount: float


class PayoutStudent(BaseModel):
    student_id: str
    name: str
    status: str
    submitted: int
    approved: int
    files_count: int
    approval_ratio: float
    impact: float
    share_pct: float
    amount: float
    project_score: float
    old_rating: Optional[float]
    new_final_rating: float


class PayoutTransaction(BaseModel):
    user_id: str
    name: str
    role: str
    kind: str
    amount: float


class PayoutOut(BaseModel):
    project_id: str
    budget: float
    student_pool: float
    researcher_pool: float
    project_fund: float
    refunded: float
    completed_at: Optional[str]
    researchers: list[PayoutResearcher]
    students: list[PayoutStudent]
    transactions: list[PayoutTransaction]
