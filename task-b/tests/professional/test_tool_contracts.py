from agent_assignment.professional.tool_contracts import (
    CONTROLLED_AGENT_INSTRUCTION,
    available_tools,
)


def test_search_tool_contract_exposes_only_controlled_query_schema():
    tools = available_tools()

    assert [item["function"]["name"] for item in tools] == ["search_documents"]
    parameters = tools[0]["function"]["parameters"]
    assert parameters["required"] == ["query"]
    assert parameters["additionalProperties"] is False
    assert "权限" in tools[0]["function"]["description"]
    assert "只能提出 search_documents" in CONTROLLED_AGENT_INSTRUCTION
