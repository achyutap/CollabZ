from pydantic import BaseModel


class StartBody(BaseModel):
    skills: list[str]


class AnswerIn(BaseModel):
    question_id: str
    selected_index: int


class SubmitBody(BaseModel):
    attempt_token: str
    answers: list[AnswerIn]
