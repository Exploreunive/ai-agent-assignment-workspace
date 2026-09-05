from collections import defaultdict
from typing import Iterable, List

from .schemas import FieldCandidate, Issue


_REQUIRED_FIELDS = {
    "market": "目标市场",
    "budget_usd": "预算",
    "channels": "合作渠道",
    "creator_count": "Creator 数量",
    "creator_topics": "Creator 覆盖主题",
    "launch_date": "上线日期",
    "rights_duration_months": "内容使用权期限",
    "paid_usage": "是否包含 PaidUsage",
}


def _values(candidates: Iterable[FieldCandidate], field_name: str) -> List[FieldCandidate]:
    return [
        item
        for item in candidates
        if item.field_name == field_name
        and item.status != "rejected"
        and item.value is not None
    ]


def check_missing_and_conflicts(fields: List[FieldCandidate]) -> List[Issue]:
    """确定性检查，不依赖模型是否“认为自己答对了”。"""
    issues: List[Issue] = []
    by_field = defaultdict(list)
    for item in fields:
        if item.status != "rejected":
            by_field[item.field_name].append(item)

    for field_name, label in _REQUIRED_FIELDS.items():
        if not _values(fields, field_name) and not by_field.get(field_name):
            missing = FieldCandidate(
                candidate_id=f"missing:{field_name}",
                field_name=field_name,
                value=None,
                fact_type="missing",
                status="needs_confirmation",
                confidence=1.0,
                note=f"当前材料未提取到{label}。",
            )
            fields.append(missing)
            by_field[field_name].append(missing)
            issues.append(
                Issue(
                    code="required_field_missing",
                    field_name=field_name,
                    severity="blocking",
                    message=f"材料中缺少{label}，不能直接生成确认版本。",
                    candidate_ids=[missing.candidate_id],
                )
            )

    launch_dates = _values(fields, "launch_date")
    if len({str(item.value) for item in launch_dates}) > 1:
        for item in launch_dates:
            item.fact_type = "conflict"
            item.status = "needs_confirmation"
        issues.append(
            Issue(
                code="date_conflict",
                field_name="launch_date",
                severity="blocking",
                message="不同材料给出了不同的上线日期，需由业务负责人确认。",
                candidate_ids=[item.candidate_id for item in launch_dates],
            )
        )

    markets = _values(fields, "market")
    inferred_markets = [item for item in markets if item.fact_type == "inferred"]
    if inferred_markets:
        for item in inferred_markets:
            item.status = "needs_confirmation"
        issues.append(
            Issue(
                code="market_confirmation_required",
                field_name="market",
                severity="blocking",
                message="加拿大市场来自会议建议，客户尚未正式确认，不能进入确认版本。",
                candidate_ids=[item.candidate_id for item in inferred_markets],
            )
        )

    rights = _values(fields, "rights_duration_months")
    paid_usage = _values(fields, "paid_usage")
    if rights and not paid_usage:
        issues.append(
            Issue(
                code="rights_scope_missing",
                field_name="paid_usage",
                severity="blocking",
                message="已提取内容使用权期限，但没有说明是否包含 PaidUsage。",
                candidate_ids=[],
            )
        )
    elif any(item.value in (None, "", "未说明") for item in by_field.get("paid_usage", [])):
        missing = by_field["paid_usage"]
        for item in missing:
            item.status = "needs_confirmation"
        issues.append(
            Issue(
                code="rights_scope_missing",
                field_name="paid_usage",
                severity="blocking",
                message="已提取内容使用权期限，但没有说明是否包含 PaidUsage。",
                candidate_ids=[item.candidate_id for item in missing],
            )
        )

    requirement_fields = [*by_field.get("product_requirement", []), *by_field.get("audience_positioning", [])]
    if len(requirement_fields) >= 2:
        issues.append(
            Issue(
                code="requirement_review",
                field_name="product_requirement",
                severity="warning",
                message="产品必须突出多色打印，同时面向低成本入门用户，建议确认传播重点和目标人群是否冲突。",
                candidate_ids=[item.candidate_id for item in requirement_fields],
            )
        )
    return issues
