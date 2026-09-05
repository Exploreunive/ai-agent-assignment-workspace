"""可选的 OpenAI-compatible 模型适配器；默认作业路径仍使用 Mock。"""

import json
from typing import Any, List
from urllib.request import Request, urlopen

from .qa_service import build_answer_messages
from .schemas import AskResponse, Citation, Evidence, SearchToolArguments, SearchToolCall
from .tool_contracts import CONTROLLED_AGENT_INSTRUCTION, available_tools


class OpenAICompatibleClient:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, messages: List[dict[str, str]], tools: list[dict] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0}
        if tools is not None:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def parse_search_tool_call(response: dict[str, Any]) -> SearchToolCall:
    message = response.get("choices", [{}])[0].get("message", {})
    calls = message.get("tool_calls") or []
    if len(calls) != 1:
        raise ValueError("模型没有返回唯一的 search_documents 工具调用")
    function = calls[0].get("function") or {}
    if function.get("name") != "search_documents":
        raise ValueError("模型返回了未开放的工具")
    raw_arguments = function.get("arguments") or "{}"
    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
    return SearchToolCall(
        name="search_documents",
        arguments=SearchToolArguments.model_validate(arguments),
    )


class OpenAICompatibleAgentModel:
    def __init__(self, client: OpenAICompatibleClient):
        self.client = client

    def decide_search(self, question: str) -> SearchToolCall:
        response = self.client.chat(
            [
                {"role": "system", "content": CONTROLLED_AGENT_INSTRUCTION},
                {"role": "user", "content": question},
            ],
            tools=available_tools(),
        )
        return parse_search_tool_call(response)


class OpenAICompatibleAnswerer:
    def __init__(self, client: OpenAICompatibleClient):
        self.client = client

    def answer(self, question: str, evidence: List[Evidence]) -> AskResponse:
        response = self.client.chat(build_answer_messages(question, evidence))
        content = response.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise ValueError("模型没有返回文本回答")
        citations = [
            Citation(
                evidence_id=item.evidence_id,
                document_id=item.document_id,
                version=item.version,
                section=item.section,
                page=item.page,
            )
            for item in evidence
        ]
        return AskResponse(status="answered", answer=content, citations=citations)
