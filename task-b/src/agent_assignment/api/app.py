from datetime import date
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

from agent_assignment.professional.retrieval import EsDocumentRepository
from agent_assignment.professional.schemas import AskRequest, AskResponse
from agent_assignment.professional.workflow import FixedQaWorkflow


app = FastAPI(title="Creator Campaign Knowledge Assistant")
repository = EsDocumentRepository(
    base_url=os.getenv("ES_URL", "http://127.0.0.1:19200"),
    index_name=os.getenv("ES_INDEX", "agent_assignment_documents"),
)
workflow = FixedQaWorkflow(repository)


@app.get("/health")
def health():
    return {"status": "ok", "service": "creator-campaign-knowledge-assistant"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(Path(__file__).resolve().parents[3] / "web" / "index.html")


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, x_user_group: str = Header(..., alias="X-User-Group")):
    if x_user_group not in {"strategy", "legal", "operations"}:
        raise HTTPException(status_code=403, detail="认证上下文中的用户组无效")
    today = date.fromisoformat(os.getenv("DEMO_TODAY", "2026-09-05"))
    return workflow.ask(request.question, x_user_group, today)
