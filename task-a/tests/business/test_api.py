import pytest
from fastapi.testclient import TestClient

from agent_assignment.api.app import app


pytestmark = pytest.mark.integration
client = TestClient(app)


def request_payload(key="api-request"):
    return {
        "request_key": key,
        "created_by": "alice",
        "materials": [{
            "material_id": "api-email",
            "material_type": "email",
            "file_name": "email.txt",
            "content": "美国市场，预算160000美元，YouTube和TikTok，20位Creator，2026-11-15上市。",
        }],
    }


def test_import_returns_traceable_fields_and_get_endpoint_returns_same_draft():
    response = client.post("/business/drafts/import", json=request_payload("api-trace"))
    assert response.status_code == 200
    body = response.json()
    assert body["fields"][0]["source_material_id"] == "api-email"

    detail = client.get(f"/business/drafts/{body['draft_id']}")
    assert detail.status_code == 200
    assert detail.json()["draft_id"] == body["draft_id"]


def test_duplicate_import_returns_original_draft_and_viewer_cannot_confirm():
    first = client.post("/business/drafts/import", json=request_payload("api-idempotent")).json()
    second = client.post("/business/drafts/import", json=request_payload("api-idempotent")).json()
    assert first["draft_id"] == second["draft_id"]

    response = client.post(
        f"/business/drafts/{first['draft_id']}/confirm",
        json={"version": 1, "operator_id": "viewer", "operator_role": "viewer"},
    )
    assert response.status_code == 403
