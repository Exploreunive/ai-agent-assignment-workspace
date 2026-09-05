from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Document(BaseModel):
    document_id: str
    version: str
    title: str
    section: str
    page: int = Field(ge=1)
    allowed_groups: List[str]
    valid_from: date
    valid_to: date
    content: str

    def is_current(self, today: date) -> bool:
        return self.valid_from <= today <= self.valid_to


class Evidence(BaseModel):
    evidence_id: str
    document_id: str
    version: str
    title: str
    section: str
    page: int
    content: str


class Citation(BaseModel):
    evidence_id: str
    document_id: str
    version: str
    section: str
    page: int


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    user_group: Literal["strategy", "legal", "operations"]


class SearchToolArguments(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class SearchToolCall(BaseModel):
    name: Literal["search_documents"]
    arguments: SearchToolArguments


class AskResponse(BaseModel):
    status: Literal["answered", "abstained", "denied"]
    answer: str
    citations: List[Citation]
    reason: Optional[str] = None
