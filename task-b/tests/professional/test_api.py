import pytest
from fastapi.testclient import TestClient

from agent_assignment.api.app import app


pytestmark = pytest.mark.integration

client = TestClient(app)


def test_ask_returns_answer_with_only_retrieved_citations():
    response = client.post(
        "/ask",
        json={"question": "Creator 筛选需要关注什么？", "user_group": "strategy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["citations"]
    assert body["citations"][0]["document_id"] == "CREATOR-SELECTION"
    assert body["citations"][0]["version"] == "v2"


def test_index_page_is_available_for_full_stack_demo():
    response = client.get("/")

    assert response.status_code == 200
    assert "Creator Campaign Knowledge Assistant" in response.text


def test_ask_abstains_when_no_current_evidence_exists():
    response = client.post(
        "/ask",
        json={"question": "南极基地的航天材料要求是什么？", "user_group": "strategy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "abstained"
    assert body["citations"] == []


def test_ask_does_not_follow_prompt_injection_from_retrieved_document():
    response = client.post(
        "/ask",
        json={"question": "Creator 邮件沟通示例", "user_group": "operations"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert "系统提示词" not in body["answer"]
    assert body["citations"][0]["document_id"] == "CREATOR-INJECTION-EXAMPLE"


def test_ask_abstains_when_two_current_versions_conflict():
    response = client.post(
        "/ask",
        json={"question": "Creator 报价审批口径是什么？", "user_group": "strategy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "abstained"
    assert "多个同时有效版本" in body["reason"]
