from datetime import date
from typing import Optional

from .policy import sanitize_untrusted_content
from .qa_service import MockAgentModel, MockAnswerer, citations_belong_to
from .retrieval import EsDocumentRepository
from .schemas import AskResponse, Evidence, SearchToolCall


class FixedQaWorkflow:
    """S2 第一版：受控 Agentic RAG，只开放一个检索工具。"""

    def __init__(
        self,
        repository: EsDocumentRepository,
        answerer: Optional[MockAnswerer] = None,
        model: Optional[MockAgentModel] = None,
    ):
        self.repository = repository
        self.answerer = answerer or MockAnswerer()
        self.model = model or MockAgentModel()

    def execute_tool(self, call: SearchToolCall, user_group: str, today: date):
        if call.name != "search_documents":
            raise ValueError("当前版本只允许调用 search_documents")
        return self.repository.search(call.arguments.query, user_group, today, limit=8)

    def get_source(self, document_id: str, version: str, section: str, user_group: str, today: date):
        """保留给 S3 的第二个受控工具；S2 不将它开放给模型。"""
        return self.repository.get_source(document_id, version, section, user_group, today)

    def ask(self, question: str, user_group: str, today: date) -> AskResponse:
        call = self.model.decide_search(question)
        result = self.execute_tool(call, user_group, today)
        if result.conflicts:
            return AskResponse(
                status="abstained",
                answer="",
                citations=[],
                reason="资料存在多个同时有效版本，需要业务人员确认后再回答。",
            )
        if not result.documents:
            return AskResponse(
                status="abstained",
                answer="",
                citations=[],
                reason="没有找到当前用户组可访问的有效资料。",
            )

        evidence = [
            Evidence(
                evidence_id="%s:%s:%s" % (item.document_id, item.version, item.section),
                document_id=item.document_id,
                version=item.version,
                title=item.title,
                section=item.section,
                page=item.page,
                content=sanitize_untrusted_content(item.content),
            )
            for item in result.documents[:4]
        ]
        response = self.answerer.answer(question, evidence)
        if not citations_belong_to(response.citations, evidence):
            return AskResponse(
                status="abstained",
                answer="",
                citations=[],
                reason="生成内容无法回指本轮检索证据。",
            )
        return response
