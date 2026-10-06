from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    role: Literal["sponsor", "researcher", "student"]
    skills: Optional[List[str]] = None
    bio: Optional[str] = None


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    role: str
    name: str
    email: str
    has_taken_quiz: bool
    pending_quiz_skills: List[str] = []


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ResearcherOut(BaseModel):
    id: str
    name: str
    skills: List[str]
    rating: float
    bio: str
    availability: float


class StudentOut(BaseModel):
    id: str
    name: str
    skills: List[str]
    temp_rating: Optional[float]
    final_rating: Optional[float]
    rating: Optional[float]
    rating_type: Optional[str]
    projects_done: int
    pending_skills: List[str] = []


class LedgerEntryOut(BaseModel):
    id: str
    amount: float
    type: str
    problem_id: Optional[str]
    project_id: Optional[str]
    created_at: str


class WalletOut(BaseModel):
    balance: float
    entries: List[LedgerEntryOut]
