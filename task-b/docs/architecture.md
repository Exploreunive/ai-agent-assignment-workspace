# Architecture Notes

## S2 请求链路

```text
Browser / curl
  -> FastAPI POST /ask
  -> AskRequest Pydantic 校验
  -> tool_contracts.py 提供 search_documents 工具说明和参数 Schema
  -> MockAgentModel 生成受控 search_documents 调用
  -> FixedQaWorkflow / Runtime 校验工具名与参数
  -> EsDocumentRepository
       -> ES bool query
       -> allowed_groups 过滤
       -> valid_from/valid_to 过滤
       -> title^3 / section^2 / content 的 BM25 检索
  -> policy 选择每个 document_id 的最新有效版本
  -> evidence projection
  -> MockAnswerer 生成回答和 citation
  -> citation validator
  -> AskResponse answered / abstained
```

## 为什么是受控 Agentic RAG

S2 仍然有 Agent 的关键边界：模型理解用户问题、产生结构化工具参数，Runtime 执行工具并把结果交回回答模块。但第一版只开放 `search_documents`，不让模型自由调用 `get_source` 或访问任意系统。这样可以把题目要求的权限、资料更新、引用和拒答验证清楚。

S3 才在相同 Runtime 上增加第二个 `get_source` 工具。模型可以根据第一次结果决定是否补取正文，但限制最多两轮，且最终只能产生待人工审批的草稿。

## 工具提示词和执行代码分别在哪里

`professional/tool_contracts.py` 是发给真实模型的工具契约：包含工具名称、用途、`query` 参数 Schema 和禁止越权的说明。`professional/schemas.py` 再用 Pydantic 校验模型实际返回的参数。`professional/workflow.py` 的 `execute_tool` 是 Runtime 入口，负责确认工具名后调用 `EsDocumentRepository`；`retrieval.py` 才负责把结构化参数转换成 Elasticsearch 查询。

当前作业为了无密钥可运行，`qa_service.py` 使用 `MockAgentModel` 模拟模型返回调用，不会真正发起模型请求。接入 OpenAI-compatible 模型时，可以把 `available_tools()` 作为请求里的 `tools` 字段，响应中的 `message.tool_calls` 仍需经过 Pydantic 和 Runtime 校验。

## 本地项目经验映射

- 既有文档问答 Agent 的循环、工具白名单、结果投影和引用校验对应本项目的受控调用入口。
- 既有文档撰写 Agent 的状态图、工具条件和依赖注入测试对应未来 S3 的多步流程；本 S2 不复制其复杂会话和编辑能力。
- 统一业务平台的职责边界对应本项目未来可接入的认证网关；当前作业用 `user_group` 模拟已认证身份，不把鉴权写成前端信任。
- 通用 Agent Harness 的共同启发是：模型循环、工具权限、事实记录、上下文和验证属于不同职责；本项目只实现题目需要的最小子集。
