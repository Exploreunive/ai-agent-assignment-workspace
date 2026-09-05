from agent_assignment.business.conflict_checker import check_missing_and_conflicts
from agent_assignment.business.extraction import MockRequirementExtractor
from agent_assignment.business.schemas import MaterialInput


def assignment_materials():
    return [
        MaterialInput(
            material_id="email-001",
            material_type="email",
            file_name="client-email.txt",
            content="美国 160000美元 YouTube TikTok 20位Creator 2026-11-15上市，内容使用权三个月。",
        ),
        MaterialInput(
            material_id="excel-001",
            material_type="excel",
            file_name="creator-plan.xlsx",
            content="目标市场美国，计划上线日期2026-11-29。",
        ),
        MaterialInput(
            material_id="chat-001",
            material_type="chat",
            file_name="client-chat.txt",
            content="覆盖Maker、家庭DIY、教育和科技评测，低成本入门用户也能理解。",
        ),
        MaterialInput(
            material_id="meeting-001",
            material_type="meeting",
            file_name="meeting-notes.docx",
            content="有人建议增加加拿大市场，但客户尚未正式确认。",
        ),
        MaterialInput(
            material_id="attachment-001",
            material_type="attachment",
            file_name="product-requirement.pdf",
            content="必须突出多色打印能力。",
        ),
    ]


def test_assignment_materials_create_required_blocking_issues_and_keep_sources():
    materials, fields = MockRequirementExtractor().extract(assignment_materials())
    issues = check_missing_and_conflicts(fields)

    assert len(materials) == 5
    assert {item.code for item in issues} >= {
        "date_conflict",
        "market_confirmation_required",
        "rights_scope_missing",
    }
    assert all(item.source_material_id for item in fields)
    assert {item.value for item in fields if item.field_name == "market"} == {"美国", "加拿大"}


def test_paid_usage_manual_candidate_clears_missing_issue():
    _, fields = MockRequirementExtractor().extract(assignment_materials())
    old_missing = next(item for item in fields if item.field_name == "paid_usage")
    old_missing.status = "rejected"
    fields.append(old_missing.model_copy(update={
        "candidate_id": "manual:paid_usage:v2",
        "value": "不包含 PaidUsage",
        "fact_type": "explicit",
        "status": "candidate",
        "source_material_id": None,
    }))

    assert "rights_scope_missing" not in {item.code for item in check_missing_and_conflicts(fields)}
