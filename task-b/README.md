# Creator Campaign Knowledge Assistant

这是初级全栈/Agent 开放题的题目 B 实现，业务语境采用 GlobalStar 公开业务中容易理解的跨市场 Creator 红人营销场景。题目要求的 S1-S3 决策表、S2 伪代码、三个固定反例和 AI 使用记录见 `decision.md`。

## 完成范围

本版本重点实现 S2：对每周更新的 Creator Campaign 资料做受控问答。

```text
用户问题
  -> 受控模型生成 search_documents 参数
  -> Runtime 校验工具名和参数
  -> Elasticsearch 先做用户组与有效期过滤
  -> BM25 检索候选资料
  -> 结果按 document_id 选择当前版本
  -> 生成带来源的回答
  -> 校验引用必须来自本轮证据
  -> 无可靠证据则 abstain
```

S2 使用受控 Agentic RAG，而不是把所有资料写入 Prompt，也不是允许模型自由访问任意工具。模型只负责理解问题并填写检索参数；用户组、资料有效期、返回数量和引用范围由服务端控制。

## 运行前准备

本项目使用本地 Elasticsearch 9.4.2，默认地址为 `http://127.0.0.1:19200`。作业实例使用独立数据目录 `.es-data`，不读写标准问答项目的真实索引。

Python 环境使用 3.12，依赖由 `uv` 管理；首次运行会自动创建项目虚拟环境。

也可以提前执行 `uv sync --python 3.12 --extra dev` 完成依赖安装。

如果 ES 尚未启动，使用已安装的 ES 9.4.2 二进制启动一个本地实例。提交版不写死 ES 安装路径，请通过 `ES_HOME` 传入路径：

```bash
ES_HOME=/path/to/elasticsearch-9.4.2 ./scripts/start_es_assignment.sh
ES_URL=http://127.0.0.1:19200 ./scripts/import_professional_es.sh
```

导入脚本会创建 `agent_assignment_documents` 索引、设置字段 mapping、批量写入 8 条合成资料并主动 refresh。资料内容是为面试编写的示例，不代表 GlobalStar 的内部规则，也不代表任何真实客户数据。

## 启动 API

```bash
PYTHONPATH=src uv run --python 3.12 uvicorn agent_assignment.api.app:app --reload --port 18081
```

打开 `http://127.0.0.1:18081/`，或直接请求：

```bash
curl -sS http://127.0.0.1:18081/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Creator 筛选需要关注什么？","user_group":"strategy"}'
```

正常结果会返回 `status=answered`、回答和 `CREATOR-SELECTION:v2:3.1` 引用；权限不匹配、资料过期或没有可靠证据时返回 `status=abstained`。

## 测试

不依赖 ES 的最低单元测试可以直接执行：

```bash
uv run --python 3.12 pytest -q -m "not integration"
```

ES 已启动并导入资料后执行完整专业题测试：

```bash
uv run --python 3.12 pytest -q tests/professional
```

当前测试覆盖：

- 当前资料和最新版本选择；
- 两组用户权限隔离；
- 过期资料不参与检索；
- 同一资料多个同日有效版本时拒答并要求人工确认；
- Prompt Injection 只作为外部资料处理；
- 引用必须回指本轮证据；
- 无可靠资料时拒答；
- Pydantic 输入约束和单一检索工具边界。

## Mock 边界

- 真实实现：Elasticsearch 索引、mapping、过滤、BM25 查询、版本选择、权限过滤、有效期过滤、引用校验和拒答。
- Mock：模型的语义决策和最终自然语言生成。`MockAgentModel` 模拟模型生成 `search_documents` 的结构化调用，`MockAnswerer` 模拟回答生成；两者都可以替换为 OpenAI-compatible 模型适配器。
- 未接入：公司内部 GlobalStar 系统、真实客户资料、外部生产模型、Embedding 服务和飞书。

工具契约位于 `src/agent_assignment/professional/tool_contracts.py`：它是给真实模型看的工具名称、用途和 JSON Schema；`schemas.py` 负责校验模型返回的参数，`workflow.py` 负责 Runtime 调度。当前默认模型是 Mock，因此不会实际请求模型厂商 API，但工具边界和参数契约已经按 OpenAI-compatible `tools` 请求格式写出。

## 为什么没有一开始做完全自主 Agent

S2 的输入是每周更新的资料，核心风险是引用过期内容和越权内容。第一版优先保证权限、版本、证据和拒答可测试。S3 才适合开放 `search_documents` 与 `get_source` 两个工具，让模型在最多两轮内自主检索、补取来源并生成待人工审批的草稿。

## 面试演示顺序

建议按“正常回答 -> 权限/过期拒答 -> 同日版本冲突拒答 -> 外部资料注入仍被当作正文”演示。这样可以直接说明：模型只负责理解问题和提出检索参数，Runtime 负责用户组、有效期、版本冲突、结果范围和引用回指；资料内容不能改变系统规则，也不能让模型获得额外工具权限。最后再说明 S3 才会在同一 Runtime 上增加 `get_source`，并限制最多两轮和人工审批。

## AI 使用说明

AI 用于拆解题目约束、检查目录设计、生成局部测试草稿和辅助阅读既有文档问答 Agent、文档撰写 Agent 与通用 Agent Harness 的实现思路。保留的建议是“按 S1/S2/S3 逐渐增加复杂度”和“把权限、版本、引用放在程序控制层”；拒绝了“所有场景都使用完全自主 Agent”和“把所有资料直接塞进 Prompt”的建议。关键行为均通过本地 ES 查询和 pytest 反例验证。
