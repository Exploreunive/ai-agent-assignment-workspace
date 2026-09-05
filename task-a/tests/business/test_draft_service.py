import pytest

from agent_assignment.business.draft_service import (
    BlockingIssues,
    DraftService,
    IdempotencyConflict,
    InvalidTransition,
    NotAuthorized,
    VersionConflict,
)
from agent_assignment.business.schemas import (
    ConfirmationRequest,
    ImportMaterialsRequest,
    MaterialInput,
    ReturnRequest,
    UpdateFieldRequest,
)


def complete_request(key="complete-001"):
    return ImportMaterialsRequest(
        request_key=key,
        created_by="alice",
        materials=[MaterialInput(
            material_id="complete-email",
            material_type="email",
            file_name="complete.txt",
            content="美国市场，预算160000美元，YouTube和TikTok，20位Creator，覆盖Maker和教育，2026-11-15上市，内容使用权三个月，不包含 PaidUsage。",
        )],
    )


def blocked_request(key="blocked-001"):
    return ImportMaterialsRequest(
        request_key=key,
        created_by="alice",
        materials=[MaterialInput(
            material_id="blocked-email",
            material_type="email",
            file_name="blocked.txt",
            content="美国市场，预算160000美元，2026-11-15上市；另一份口径写2026-11-29上市，内容使用权三个月。",
        )],
    )


def test_import_is_idempotent_and_keeps_one_draft():
    service = DraftService()
    request = complete_request("same-request")

    first = service.import_materials(request)
    second = service.import_materials(request)

    assert first.draft_id == second.draft_id
    assert first.version == second.version == 1


def test_same_request_key_with_changed_materials_is_rejected():
    service = DraftService()
    service.import_materials(complete_request("fingerprint-request"))
    changed = complete_request("fingerprint-request")
    changed.materials[0].content += " 客户补充了付款条件。"

    with pytest.raises(IdempotencyConflict):
        service.import_materials(changed)


def test_blocking_issues_prevent_confirmation_until_manual_revisions():
    service = DraftService()
    draft = service.import_materials(blocked_request("revision-request"))
    assert draft.status == "draft"

    revised = service.update_field(
        draft.draft_id,
        "launch_date",
        UpdateFieldRequest(version=1, operator_id="alice", value="2026-11-15"),
    )
    assert revised.version == 2
    assert revised.audit_log[-1].action == "field_update"
    assert revised.audit_log[-1].operator_id == "alice"
    with pytest.raises(BlockingIssues):
        service.confirm(
            draft.draft_id,
            ConfirmationRequest(version=2, operator_id="manager", operator_role="project_owner"),
        )


def test_confirm_requires_role_and_current_version_then_records_operator():
    service = DraftService()
    draft = service.import_materials(complete_request("confirm-request"))

    with pytest.raises(NotAuthorized):
        service.confirm(
            draft.draft_id,
            ConfirmationRequest(version=1, operator_id="viewer", operator_role="viewer"),
        )
    with pytest.raises(VersionConflict):
        service.confirm(
            draft.draft_id,
            ConfirmationRequest(version=2, operator_id="manager", operator_role="project_owner"),
        )
    confirmed = service.confirm(
        draft.draft_id,
        ConfirmationRequest(version=1, operator_id="manager", operator_role="project_owner"),
    )

    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_by == "manager"
    assert [item.action for item in confirmed.audit_log] == ["import", "confirm"]
    with pytest.raises(InvalidTransition):
        service.confirm(
            draft.draft_id,
            ConfirmationRequest(version=1, operator_id="manager", operator_role="project_owner"),
        )


def test_return_preserves_reason_and_does_not_delete_materials():
    service = DraftService()
    draft = service.import_materials(complete_request("return-request"))

    returned = service.return_draft(
        draft.draft_id,
        ReturnRequest(
            version=1,
            operator_id="owner",
            operator_role="project_owner",
            note="补充客户确认的上线日期",
        ),
    )

    assert returned.status == "returned"
    assert returned.return_note == "补充客户确认的上线日期"
    assert returned.materials[0].material_id == "complete-email"
