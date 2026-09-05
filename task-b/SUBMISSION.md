# 题目 B 提交说明

## 开始前说明

选择题目 B，是因为它最接近我做过的标准问答 Agent，能够在一个小闭环中展示检索、工具调用、权限、版本、引用、拒答和测试治理能力。没有做过的是 CreatorOS 的真实内部业务系统、真实客户资料和生产模型接入；本作业不假设这些内部条件。准备先完成的最小闭环是：输入问题 -> 按用户组和有效期检索 -> 返回带引用的回答，查不到、越权、过期或版本冲突时拒答。

本提交重点实现 S2 每周更新资料问答，并保留 S1、S3 的第一版方案决策和升级边界。

与真实项目的差异是：这里不使用公司内部资料、接口或密钥，Creator Campaign 文档均为便于演示而编写的合成数据；模型调用使用 Mock，Elasticsearch 检索、权限/有效期过滤、同日版本冲突、引用校验和 Prompt Injection 防护是真实实现并有测试覆盖。

题目要求的三行决策表和不超过 30 行的伪代码在 `decision.md`；运行方式、Mock 边界和面试演示顺序在 `README.md`。S1 和 S3 保留设计决策，第一版只实现 S2，避免为了展示 Agent 而引入不必要的自由循环。

AI 使用与验证：AI 用于拆解题目约束、比较 S1-S3 的第一版方案、检查反例覆盖、生成局部测试草稿和辅助阅读已有 Agent 项目。保留了“按复杂度递进”“权限、版本和引用由程序控制”的建议；拒绝了“所有场景都做完全自主 Agent”“把所有资料直接放进 Prompt”“让模型决定权限和有效版本”等建议。关键结果通过本地 Elasticsearch 的真实过滤/检索、同日版本冲突测试、权限/过期测试、Prompt Injection 测试和 API 测试验证。

未完成项与后续优先级：第一版没有接入真实模型、公司内部系统或 Embedding 服务，也没有实现 S3 的多轮草稿 Agent。若继续完善，优先接入真实 OpenAI-compatible 模型适配器并保留现有 Runtime 校验，再增加 S3 的 `get_source` 两轮补取和人工审批；不会先扩展成无限自主 Agent。

最小运行顺序：

```bash
uv sync --python 3.12 --extra dev
ES_HOME=/path/to/elasticsearch-9.4.2 ./scripts/start_es_assignment.sh
./scripts/import_professional_es.sh
PYTHONPATH=src uv run --python 3.12 uvicorn agent_assignment.api.app:app --port 18081
```

测试命令：

```bash
uv run --python 3.12 pytest -q -m "not integration"  # 无 ES 的最低测试
uv run --python 3.12 pytest -q                       # 启动 ES 后的完整回归
```
