from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from agent_assignment.business.draft_service import (
    BlockingIssues,
    DraftNotFound,
    DraftService,
    IdempotencyConflict,
    InvalidTransition,
    NotAuthorized,
    VersionConflict,
)
from agent_assignment.business.schemas import (
    ConfirmationRequest,
    Draft,
    ImportMaterialsRequest,
    ReturnRequest,
    UpdateFieldRequest,
)


app = FastAPI(title="Creator Campaign Requirement Drafting")
service = DraftService()


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, DraftNotFound):
        return HTTPException(status_code=404, detail="Draft 不存在")
    if isinstance(exc, NotAuthorized):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, (VersionConflict, IdempotencyConflict)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, (BlockingIssues, InvalidTransition)):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@app.get("/health")
def health():
    return {"status": "ok", "service": "creator-campaign-requirement-drafting"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(Path(__file__).resolve().parents[3] / "web" / "index.html")


@app.post("/business/drafts/import", response_model=Draft)
def import_draft(request: ImportMaterialsRequest):
    return service.import_materials(request)


@app.get("/business/drafts/{draft_id}", response_model=Draft)
def get_draft(draft_id: str):
    try:
        return service.current(draft_id)
    except Exception as exc:
        raise _error(exc) from exc


@app.patch("/business/drafts/{draft_id}/fields/{field_name}", response_model=Draft)
def update_field(draft_id: str, field_name: str, request: UpdateFieldRequest):
    try:
        return service.update_field(draft_id, field_name, request)
    except Exception as exc:
        raise _error(exc) from exc


@app.post("/business/drafts/{draft_id}/confirm", response_model=Draft)
def confirm(draft_id: str, request: ConfirmationRequest):
    try:
        return service.confirm(draft_id, request)
    except Exception as exc:
        raise _error(exc) from exc


@app.post("/business/drafts/{draft_id}/return", response_model=Draft)
def return_draft(draft_id: str, request: ReturnRequest):
    try:
        return service.return_draft(draft_id, request)
    except Exception as exc:
        raise _error(exc) from exc
