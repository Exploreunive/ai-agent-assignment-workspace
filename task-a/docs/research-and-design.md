# 题目 A 调研与设计依据

## 先说结论

这个场景不适合让 Agent 直接把多份材料合并成最终需求。更稳妥的主链是：材料接入 -> AI 提取候选 -> 保存每个候选的来源 -> 程序检查缺失和冲突 -> 人工确认 -> 生成可供下游使用的 Confirmed 版本。

AI 可以帮助业务人员减少阅读和整理工作，但不能替业务人员确认加拿大市场、选择冲突日期或决定 PaidUsage 是否包含在 Rights 中。

## 外部资料带来的设计约束

1. [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)强调应明确人和 AI 的职责、知识边界、人工监督和评测方式。因此本项目把 `candidate`、`needs_confirmation`、`confirmed` 分开，确认动作必须带操作人和角色。
2. [NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)强调记录数据来源和来源链路。因此每个字段候选都保留 `source_material_id`、原文摘录、事实类型和版本，不能只存 AI 最终填出的值。
3. [OWASP Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)将邮件、文档、网页等外部内容视为不可信输入。本项目虽然 A 题不要求做 Prompt Injection，但材料正文仍只作为数据进入抽取器，不能改变确认权限和状态规则。
4. [Gmail API reference](https://developers.google.com/workspace/gmail/api/reference/rest)提供 thread、message、attachment 和 history 等资源，说明真实接入时应保留外部消息 ID、线程 ID、附件 ID 和增量同步信息，而不是只保存一段脱离来源的文本。本项目用 `material_id` 模拟这一层。

## 本地项目经验映射

- 标准撰写 Agent 的 `StateGraph`、阶段状态和人工 checkpoint 对应 A 题的 Draft -> Confirmed 生命周期；A 题将确认作为明确状态转换，而不是在 Prompt 中说“请确认”。
- 标准问答 Agent 的证据投影、来源 ID 和 Claim 回指对应 A 题的字段来源追溯；候选字段必须能回到原材料。
- 综合平台的 Java 鉴权和操作边界对应 A 题的确认角色校验；当前用 `operator_role` 模拟已认证用户，不能信任前端传来的“我是管理员”文字。

## 为什么允许 Mock

题目允许 Mock 文件解析、OCR、模型调用和飞书，所以 `MockRequirementExtractor` 只负责模拟从五类材料中提出候选。真正不能 Mock 的部分是：候选来源保存、日期冲突、未确认市场、Rights/PaidUsage 缺失、版本递增、重复请求、确认角色和状态转换。

当前 Draft 仓储是内存实现，方便面试官零依赖运行；生产替换为 PostgreSQL 时，保留相同的 Service 接口，并把版本检查和状态变更放进事务与乐观锁即可。
