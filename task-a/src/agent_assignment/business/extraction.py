from datetime import datetime, timezone
from typing import List

from .schemas import FieldCandidate, Material, MaterialInput


def _candidate(
    field_name: str,
    value,
    material: Material,
    fact_type: str = "explicit",
    status: str = "candidate",
    confidence: float = 0.96,
    note: str | None = None,
) -> FieldCandidate:
    return FieldCandidate(
        candidate_id=f"{field_name}:{material.material_id}",
        field_name=field_name,
        value=value,
        fact_type=fact_type,
        status=status,
        confidence=confidence,
        source_material_id=material.material_id,
        source_excerpt=material.content[:240],
        note=note,
    )


class MockRequirementExtractor:
    """模拟文件解析和模型抽取；每个候选仍绑定原材料，便于回溯。"""

    def extract(self, inputs: List[MaterialInput]) -> tuple[List[Material], List[FieldCandidate]]:
        imported_at = datetime.now(timezone.utc)
        materials = [
            Material(
                material_id=item.material_id,
                material_type=item.material_type,
                file_name=item.file_name,
                content=item.content,
                imported_at=imported_at,
            )
            for item in inputs
        ]
        fields: List[FieldCandidate] = []
        for material in materials:
            text = material.content
            if "160000" in text or "160,000" in text:
                fields.append(_candidate("budget_usd", 160000, material))
            if "YouTube" in text or "TikTok" in text:
                fields.append(_candidate("channels", ["YouTube", "TikTok"], material))
            if "20" in text and "Creator" in text:
                fields.append(_candidate("creator_count", 20, material))
            if "美国" in text:
                fields.append(_candidate("market", "美国", material))
            if "加拿大" in text:
                fields.append(
                    _candidate(
                        "market",
                        "加拿大",
                        material,
                        fact_type="inferred",
                        status="needs_confirmation",
                        confidence=0.72,
                        note="会议中提出的建议，客户尚未正式确认。",
                    )
                )
            if "Maker" in text or "家庭DIY" in text or "教育" in text or "科技评测" in text:
                fields.append(
                    _candidate(
                        "creator_topics",
                        ["Maker", "家庭DIY", "教育", "科技评测"],
                        material,
                    )
                )
            if "不包含 PaidUsage" in text:
                fields.append(_candidate("paid_usage", "不包含 PaidUsage", material))
            elif "包含 PaidUsage" in text:
                fields.append(_candidate("paid_usage", "包含 PaidUsage", material))
            if "2026-11-15" in text:
                fields.append(_candidate("launch_date", "2026-11-15", material))
            if "2026-11-29" in text:
                fields.append(_candidate("launch_date", "2026-11-29", material))
            if "三个月" in text:
                fields.append(_candidate("rights_duration_months", 3, material))
            if "多色打印" in text:
                fields.append(_candidate("product_requirement", "必须突出多色打印能力", material))
            if "低成本入门" in text:
                fields.append(_candidate("audience_positioning", "低成本入门用户也能理解和使用", material))

        rights = next((item for item in materials if "三个月" in item.content), None)
        if rights and not any(item.field_name == "paid_usage" for item in fields):
            fields.append(
                _candidate(
                    "paid_usage",
                    None,
                    rights,
                    fact_type="missing",
                    status="needs_confirmation",
                    confidence=1.0,
                    note="材料只说明三个月 Rights，未说明是否包含 PaidUsage。",
                )
            )
        return materials, fields
