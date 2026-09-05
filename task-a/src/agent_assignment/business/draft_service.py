from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Dict, List, Optional
from uuid import uuid4

from .conflict_checker import check_missing_and_conflicts
from .extraction import MockRequirementExtractor
from .schemas import (
    ConfirmationRequest,
    Draft,
    FieldCandidate,
    AuditEvent,
    ImportMaterialsRequest,
    ReturnRequest,
    UpdateFieldRequest,
)


class DraftError(Exception):
    pass


class DraftNotFound(DraftError):
    pass


class VersionConflict(DraftError):
    pass


class NotAuthorized(DraftError):
    pass


class InvalidTransition(DraftError):
    pass


class BlockingIssues(DraftError):
    pass


class IdempotencyConflict(DraftError):
    pass


class DraftService:
    """内存版 Draft 仓储，接口和状态转换可替换为 PostgreSQL。"""

    CONFIRM_ROLES = {"business_manager", "project_owner"}

    def __init__(self, extractor: Optional[MockRequirementExtractor] = None):
        self.extractor = extractor or MockRequirementExtractor()
        self._drafts: Dict[str, List[Draft]] = {}
        self._request_index: Dict[str, str] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _fingerprint(request: ImportMaterialsRequest) -> str:
        payload = [item.model_dump(mode="json") for item in request.materials]
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def import_materials(self, request: ImportMaterialsRequest) -> Draft:
        existing_id = self._request_index.get(request.request_key)
        fingerprint = self._fingerprint(request)
        if existing_id:
            existing = self.current(existing_id)
            if existing.request_fingerprint != fingerprint:
                raise IdempotencyConflict("相同 request_key 对应的材料内容已发生变化")
            return existing

        materials, fields = self.extractor.extract(request.materials)
        now = self._now()
        draft = Draft(
            draft_id=f"draft-{uuid4().hex[:10]}",
            request_key=request.request_key,
            request_fingerprint=fingerprint,
            version=1,
            status="draft",
            created_by=request.created_by,
            updated_by=request.created_by,
            materials=materials,
            fields=fields,
            issues=check_missing_and_conflicts(fields),
            audit_log=[AuditEvent(
                action="import",
                operator_id=request.created_by,
                version=1,
                note="创建 Draft 并保存原始材料与 AI 候选",
                occurred_at=now,
            )],
            created_at=now,
            updated_at=now,
        )
        self._drafts[draft.draft_id] = [draft]
        self._request_index[request.request_key] = draft.draft_id
        return deepcopy(draft)

    def current(self, draft_id: str) -> Draft:
        try:
            return deepcopy(self._drafts[draft_id][-1])
        except (KeyError, IndexError) as exc:
            raise DraftNotFound(draft_id) from exc

    def _mutable_current(self, draft_id: str, version: int) -> Draft:
        current = self.current(draft_id)
        if current.version != version:
            raise VersionConflict(f"当前版本是 {current.version}，请求版本是 {version}")
        return current

    def update_field(self, draft_id: str, field_name: str, request: UpdateFieldRequest) -> Draft:
        current = self._mutable_current(draft_id, request.version)
        if current.status == "confirmed":
            # 已确认版本不能覆盖，修订会产生新的 Draft 版本。
            pass
        if current.status == "returned":
            pass

        fields = deepcopy(current.fields)
        old_candidates = [item for item in fields if item.field_name == field_name and item.status != "rejected"]
        for item in old_candidates:
            item.status = "rejected"
        fields.append(
            FieldCandidate(
                candidate_id=f"manual:{field_name}:v{current.version + 1}",
                field_name=field_name,
                value=request.value,
                fact_type="explicit",
                status="candidate",
                confidence=1.0,
                note=f"由 {request.operator_id} 人工修改，待最终确认。",
            )
        )
        return self._append_revision(current, fields, request.operator_id)

    def _append_revision(self, current: Draft, fields: List[FieldCandidate], operator_id: str) -> Draft:
        now = self._now()
        revised = current.model_copy(deep=True)
        revised.version = current.version + 1
        revised.status = "draft"
        revised.updated_by = operator_id
        revised.confirmed_by = None
        revised.confirmed_at = None
        revised.return_note = None
        revised.fields = fields
        revised.issues = check_missing_and_conflicts(fields)
        revised.audit_log.append(AuditEvent(
            action="field_update",
            operator_id=operator_id,
            version=revised.version,
            field_name=fields[-1].field_name,
            old_value=[item.value for item in current.fields if item.field_name == fields[-1].field_name and item.status != "rejected"],
            new_value=fields[-1].value,
            note="人工修改候选字段，旧候选保留在历史版本中",
            occurred_at=now,
        ))
        revised.updated_at = now
        self._drafts[current.draft_id].append(revised)
        return deepcopy(revised)

    def confirm(self, draft_id: str, request: ConfirmationRequest) -> Draft:
        current = self._mutable_current(draft_id, request.version)
        if request.operator_role not in self.CONFIRM_ROLES:
            raise NotAuthorized("只有 business_manager 或 project_owner 可以确认")
        if current.status == "confirmed":
            raise InvalidTransition("当前版本已经确认，不能重复确认")
        blocking = [item for item in current.issues if item.severity == "blocking"]
        if blocking:
            raise BlockingIssues("仍有未处理的缺失或冲突：" + "、".join(item.code for item in blocking))

        confirmed = current.model_copy(deep=True)
        confirmed.status = "confirmed"
        confirmed.updated_by = request.operator_id
        confirmed.confirmed_by = request.operator_id
        confirmed.confirmed_at = self._now()
        confirmed.fields = [
            item.model_copy(update={"status": "confirmed"})
            if item.status != "rejected" else item
            for item in confirmed.fields
        ]
        confirmed.updated_at = self._now()
        confirmed.audit_log.append(AuditEvent(
            action="confirm",
            operator_id=request.operator_id,
            operator_role=request.operator_role,
            version=confirmed.version,
            note="人工确认 Draft 版本",
            occurred_at=confirmed.confirmed_at or self._now(),
        ))
        self._drafts[draft_id].append(confirmed)
        return deepcopy(confirmed)

    def return_draft(self, draft_id: str, request: ReturnRequest) -> Draft:
        current = self._mutable_current(draft_id, request.version)
        if request.operator_role not in self.CONFIRM_ROLES:
            raise NotAuthorized("只有 business_manager 或 project_owner 可以退回")
        if current.status == "confirmed":
            raise InvalidTransition("已确认版本不能直接退回")
        returned = current.model_copy(deep=True)
        returned.status = "returned"
        returned.updated_by = request.operator_id
        returned.return_note = request.note
        returned.updated_at = self._now()
        returned.audit_log.append(AuditEvent(
            action="return",
            operator_id=request.operator_id,
            operator_role=request.operator_role,
            version=returned.version,
            note=request.note,
            occurred_at=returned.updated_at,
        ))
        self._drafts[draft_id].append(returned)
        return deepcopy(returned)
