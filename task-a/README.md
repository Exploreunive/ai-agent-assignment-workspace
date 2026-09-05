# Creator Campaign Requirement Drafting

这是初级全栈/Agent 开放题的题目 A 实现：把邮件、Excel、聊天记录、会议纪要和附件中的 Creator Campaign 需求整理成可追溯 Draft，并在缺失和冲突处理后由授权人员确认成下游可用的版本。

## 开始前说明

选择题目 A，是因为它最能体现我对真实业务材料、结构化抽取、来源追溯、冲突处理和人工确认边界的理解。最接近的经验是标准撰写 Agent 中的结构化产物、阶段状态和人工 checkpoint；没有做过的是 GlobalStar 的真实内部系统、Gmail/飞书生产接入和真实客户材料处理。准备先完成的最小闭环是：导入五类材料 -> 生成带来源的字段候选 -> 检查缺失/冲突 -> 授权人员确认或退回。

## 设计主链

```text
多种材料
  -> Mock 解析/模型抽取候选
  -> 候选绑定来源材料和原文摘录
  -> 确定性检查缺失、冲突和未确认事实
  -> Draft 页面查看和人工修改
  -> 版本递增
  -> business_manager/project_owner 确认或退回
  -> Confirmed 版本供下游读取
```

这个版本选择“受控工作流”，不让模型直接发布最终需求。AI 负责提取候选，程序负责来源、冲突、版本、幂等和权限，人工负责业务确认。题目 A 的五类材料使用容易理解的桌面多色 3D 打印机营销案例，数据为合成数据，不代表真实客户信息。

## 已完成范围

- `POST /business/drafts/import`：导入材料并创建 Draft；同一 `request_key` 重复提交返回原 Draft。
- `GET /business/drafts/{draft_id}`：查看原始材料、候选字段、来源摘录、事实类型、状态和问题。
- `PATCH /business/drafts/{draft_id}/fields/{field_name}`：人工修改候选，旧候选保留并标记为 `rejected`，新值生成下一版本。
- `POST /business/drafts/{draft_id}/confirm`：授权角色确认；有阻塞问题、版本过期或无权限时拒绝。
- `POST /business/drafts/{draft_id}/return`：授权角色退回并保留退回原因。
- 页面支持导入示例、查看来源和问题、编辑字段、确认或退回。

固定反例已实现：上线日期冲突、加拿大市场未正式确认、Rights 已有期限但 PaidUsage 未说明、重复导入、未授权确认、确认后版本不可直接覆盖。

## 未完成项与后续优先级

当前没有接入真实 Gmail、Excel/OCR、飞书或生产数据库，文件解析和模型候选抽取使用 Mock；Draft 仓储也使用内存实现。若继续完善，优先把材料仓储和状态变更迁移到 PostgreSQL，并接入真实材料解析适配器，同时保留现有来源追溯、版本校验和人工确认规则；不会先放开模型直接发布确认版本。

## 运行

```bash
uv sync --python 3.12 --extra dev
PYTHONPATH=src uv run --python 3.12 uvicorn agent_assignment.api.app:app --port 18082
```

打开 `http://127.0.0.1:18082/`。最低测试一条命令运行：

```bash
uv run --python 3.12 pytest -q
```

## Mock 和真实实现边界

- Mock：文件解析、OCR、模型候选抽取、飞书接入。
- 真实实现：候选与来源绑定、缺失检查、日期冲突、未确认市场、Rights/PaidUsage 检查、版本递增、重复请求幂等、确认/退回状态转换和角色权限。
- 当前存储：内存版 Draft 仓储，保证无数据库也能运行；生产环境可替换为 PostgreSQL，Service 接口和业务规则不变。

## AI 使用与验证

AI 用于拆解题目 A 的字段和状态要求、比较“直接生成最终结果”与“候选 + 人工确认”的方案、辅助设计测试和检查遗漏。没有采用让 Agent 自由合并资料并直接发布的建议，因为日期、市场和 PaidUsage 都属于高风险业务事实；也没有让模型自行决定权限或覆盖旧版本。

关键结果通过题目样例材料、确定性冲突检查、Draft Service 单测、API 测试和确认状态测试验证。外部调研与本地项目映射见 `docs/research-and-design.md`。
