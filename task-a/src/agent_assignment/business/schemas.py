from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


MaterialType = Literal["email", "excel", "chat", "meeting", "attachment"]
FactType = Literal["explicit", "inferred", "missing", "conflict"]
CandidateStatus = Literal["candidate", "needs_confirmation", "confirmed", "rejected"]
DraftStatus = Literal["draft", "confirmed", "returned"]


class MaterialInput(BaseModel):
    material_id: str = Field(min_length=1, max_length=80)
    material_type: MaterialType
    file_name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)


class Material(BaseModel):
    material_id: str
    material_type: MaterialType
    file_name: str
    content: str
    imported_at: datetime


class FieldCandidate(BaseModel):
    candidate_id: str
    field_name: str
    value: Any = None
    fact_type: FactType
    status: CandidateStatus
    confidence: float = Field(ge=0, le=1)
    source_material_id: Optional[str] = None
    source_excerpt: Optional[str] = None
    note: Optional[str] = None


class Issue(BaseModel):
    code: str
    field_name: str
    severity: Literal["warning", "blocking"]
    message: str
    candidate_ids: List[str] = Field(default_factory=list)


class Draft(BaseModel):
    draft_id: str
    request_key: str
    version: int = Field(ge=1)
    status: DraftStatus
    created_by: str
    updated_by: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    return_note: Optional[str] = None
    materials: List[Material]
    fields: List[FieldCandidate]
    issues: List[Issue]
    created_at: datetime
    updated_at: datetime


class ImportMaterialsRequest(BaseModel):
    request_key: str = Field(min_length=1, max_length=100)
    created_by: str = Field(min_length=1, max_length=80)
    materials: List[MaterialInput] = Field(min_length=1, max_length=20)


class UpdateFieldRequest(BaseModel):
    version: int = Field(ge=1)
    operator_id: str = Field(min_length=1, max_length=80)
    value: Any


class ConfirmationRequest(BaseModel):
    version: int = Field(ge=1)
    operator_id: str = Field(min_length=1, max_length=80)
    operator_role: Literal["business_manager", "project_owner", "viewer"]


class ReturnRequest(ConfirmationRequest):
    note: str = Field(min_length=1, max_length=500)
