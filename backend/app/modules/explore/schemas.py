from pydantic import BaseModel


class PersonCard(BaseModel):
    id: str
    name: str
    role: str
    headline: str
    skills: list[str]
    rating: float | None
    likes_count: int
