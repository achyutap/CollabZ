from pydantic import BaseModel


class ProfilePatch(BaseModel):
    name: str | None = None
    headline: str | None = None
    about: str | None = None
    location: str | None = None
    links: dict[str, str] | None = None
    details: dict | None = None
    add_skills: list[str] | None = None
    remove_skills: list[str] | None = None
