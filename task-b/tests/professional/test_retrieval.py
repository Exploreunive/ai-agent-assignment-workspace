from datetime import date

import pytest

from agent_assignment.professional.retrieval import EsDocumentRepository


ES_URL = "http://127.0.0.1:19200"


def repository() -> EsDocumentRepository:
    return EsDocumentRepository(
        base_url=ES_URL,
        index_name="agent_assignment_documents",
    )


@pytest.mark.integration
def test_search_returns_current_research_evidence_with_citation_fields():
    result = repository().search("Creator 筛选", "strategy", date(2026, 9, 5), limit=8)

    assert result.documents
    assert result.documents[0].document_id == "CREATOR-SELECTION"
    assert result.documents[0].version == "v2"
    assert result.documents[0].section == "3.1"
    assert result.documents[0].page == 6


@pytest.mark.integration
def test_search_does_not_return_operations_only_material_to_research_user():
    result = repository().search("项目效果报告口径", "strategy", date(2026, 9, 5), limit=8)

    assert result.documents == []


@pytest.mark.integration
def test_search_does_not_return_expired_material():
    result = repository().search("过期资料", "operations", date(2026, 9, 5), limit=8)

    assert result.documents == []


@pytest.mark.integration
def test_get_source_rechecks_group_and_current_version():
    evidence = repository().get_source(
        "RIGHTS-PAID-USAGE", "v2", "4.2", "legal", date(2026, 9, 5)
    )

    assert evidence is not None
    assert evidence.document_id == "RIGHTS-PAID-USAGE"
    assert repository().get_source(
        "RIGHTS-PAID-USAGE", "v2", "4.2", "research", date(2026, 9, 5)
    ) is None


@pytest.mark.integration
def test_same_effective_date_versions_return_conflict_instead_of_silent_choice():
    result = repository().search("Creator 报价审批", "strategy", date(2026, 9, 5), limit=8)

    assert result.documents == []
    assert result.conflicts == ["CREATOR-RATE-CARD"]
