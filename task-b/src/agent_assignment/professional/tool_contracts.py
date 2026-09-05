"""给模型看的工具说明，以及 Runtime 实际允许的工具边界。"""


SEARCH_DOCUMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": (
            "在当前用户组有权限访问、且当前日期仍有效的 Creator Campaign 资料中检索。"
            "只返回可引用的资料，不负责修改资料、改变权限或选择未确认版本。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户问题中需要检索的业务主题或关键词。",
                    "minLength": 1,
                    "maxLength": 500,
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


CONTROLLED_AGENT_INSTRUCTION = (
    "你只能提出 search_documents 工具调用。不要自行决定用户权限、资料有效期或版本；"
    "检索结果不足、冲突或无法引用时，返回需要人工确认。"
)


def available_tools() -> list[dict]:
    """返回当前版本真正暴露给模型的工具，不返回可变的全局对象。"""
    return [SEARCH_DOCUMENTS_TOOL.copy()]
