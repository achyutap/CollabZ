from pydantic import BaseModel, Field


class RequestsCreate(BaseModel):
    researcher_ids: list[str] = Field(min_length=1, max_length=5)


class RespondBody(BaseModel):
    accept: bool
