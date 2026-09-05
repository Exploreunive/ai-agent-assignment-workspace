from datetime import date
import json
import re
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .policy import resolve_current_documents
from .schemas import Document, Evidence


_QUERY_STOPWORDS = {"什么", "如何", "怎么", "需要", "关注", "有哪些", "哪些", "说明", "是什么", "有什么", "区别", "吗", "的"}


def _query_terms(text: str) -> List[str]:
    terms = [item.lower() for item in re.findall(r"[A-Za-z0-9_]+", text or "")]
    compact = re.sub(r"\s+", "", "".join(re.findall(r"[\u4e00-\u9fff]+", text or "")))
    terms.extend(
        compact[index:index + 2]
        for index in range(max(0, len(compact) - 1))
        if compact[index:index + 2] not in _QUERY_STOPWORDS
    )
    return [term for term in terms if term]


def _has_lexical_overlap(query: str, document: Document) -> bool:
    terms = _query_terms(query)
    title = document.title.lower()
    haystack = (title + " " + document.section + " " + document.content).lower()
    ascii_terms = [term for term in terms if re.fullmatch(r"[a-z0-9_]+", term)]
    cjk_terms = [term for term in terms if not re.fullmatch(r"[a-z0-9_]+", term)]
    title_matches = sum(term in title for term in terms)
    content_matches = sum(term in haystack for term in terms)
    title_cjk_matches = sum(term in title for term in cjk_terms)
    content_cjk_matches = sum(term in haystack for term in cjk_terms)
    return (
        title_matches >= 2
        or (ascii_terms and title_cjk_matches >= 1)
        or (len(cjk_terms) >= 2 and content_cjk_matches >= 2)
        or (not cjk_terms and content_matches >= 1)
    )


class SearchResult:
    def __init__(self, documents: List[Document], total: int, conflicts: Optional[List[str]] = None):
        self.documents = documents
        self.total = total
        self.conflicts = conflicts or []


class EsDocumentRepository:
    def __init__(self, base_url: str = "http://127.0.0.1:19200", index_name: str = "agent_assignment_documents"):
        self.base_url = base_url.rstrip("/")
        self.index_name = index_name

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        request = Request(
            self.base_url + path,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, URLError) as exc:
            raise RuntimeError("Elasticsearch 查询服务不可用") from exc

    def search(self, query: str, user_group: str, today: date, limit: int = 8) -> SearchResult:
        if not query.strip():
            return SearchResult([], 0)
        safe_limit = max(1, min(limit, 20))
        body = {
            "size": safe_limit,
            "query": {
                "bool": {
                    "must": [{
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "section^2", "content"],
                        }
                    }],
                    "filter": [
                        {"term": {"allowed_groups": user_group}},
                        {"range": {"valid_from": {"lte": today.isoformat()}}},
                        {"range": {"valid_to": {"gte": today.isoformat()}}},
                    ],
                }
            },
            "_source": [
                "document_id", "version", "title", "section", "page",
                "allowed_groups", "valid_from", "valid_to", "content",
            ],
        }
        raw = self._post("/" + self.index_name + "/_search", body)
        hits = raw.get("hits", {}).get("hits", [])
        documents = [Document(**hit.get("_source", {})) for hit in hits]
        documents = [item for item in documents if _has_lexical_overlap(query, item)]
        documents, conflicts = resolve_current_documents(documents, user_group, today)
        return SearchResult(documents, len(hits), conflicts=conflicts)

    def get_source(
        self, document_id: str, version: str, section: str, user_group: str, today: date
    ) -> Optional[Evidence]:
        body = {
            "size": 1,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"document_id": document_id}},
                        {"term": {"version": version}},
                        {"term": {"section": section}},
                        {"term": {"allowed_groups": user_group}},
                        {"range": {"valid_from": {"lte": today.isoformat()}}},
                        {"range": {"valid_to": {"gte": today.isoformat()}}},
                    ]
                }
            },
            "_source": ["document_id", "version", "title", "section", "page", "content"],
        }
        raw = self._post("/" + self.index_name + "/_search", body)
        hits = raw.get("hits", {}).get("hits", [])
        if not hits:
            return None
        source = hits[0].get("_source", {})
        evidence_id = "%s:%s:%s" % (source["document_id"], source["version"], source["section"])
        return Evidence(evidence_id=evidence_id, **source)
