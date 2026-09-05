from collections import defaultdict
from datetime import date
import re
from typing import Iterable, List

from .schemas import Document


_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?.{0,120}(system\s+prompt|instructions?)?", re.I | re.S),
    re.compile(r"忽略.{0,20}(之前|前面|所有).{0,20}指令", re.I | re.S),
    re.compile(r"(输出|泄露|透露).{0,20}系统提示词", re.I | re.S),
)


def contains_prompt_injection(content: str) -> bool:
    return any(pattern.search(content or "") for pattern in _INJECTION_PATTERNS)


def sanitize_untrusted_content(content: str) -> str:
    cleaned = content or ""
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[外部资料中的指令已忽略]", cleaned)
    return cleaned


def filter_current_documents(
    documents: Iterable[Document], user_group: str, today: date
) -> List[Document]:
    selected, _ = resolve_current_documents(documents, user_group, today)
    return selected


def resolve_current_documents(
    documents: Iterable[Document], user_group: str, today: date
) -> tuple[List[Document], List[str]]:
    visible = [
        document
        for document in documents
        if user_group in document.allowed_groups and document.is_current(today)
    ]
    grouped = defaultdict(list)
    for document in visible:
        grouped[document.document_id].append(document)

    selected = []
    conflicts = []
    selected_ids = set()
    for document in visible:
        candidates = grouped[document.document_id]
        if document.document_id in selected_ids:
            continue
        candidates.sort(key=lambda item: (item.valid_from, item.version), reverse=True)
        newest_date = candidates[0].valid_from
        if sum(item.valid_from == newest_date for item in candidates) > 1:
            conflicts.append(document.document_id)
            selected_ids.add(document.document_id)
            continue
        selected.append(candidates[0])
        selected_ids.add(document.document_id)
    return selected, conflicts
