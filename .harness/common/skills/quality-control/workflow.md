# 质量控制工作流

## 初始化

1. 读取 `.harness/common/protocols/README.md`
2. 读取 `.harness/common/protocols/quality-control/PROTOCOL.md`
3. 读取当前任务的任务契约、相关阶段文档、execution-brief、验证报告 / code-review（如存在）
4. 调用 `harness-cli` 执行 `harness context check --json`；PASS 则读取 `project-context.md`，FAIL 时按 `project-context` 规则记录 `inputs_missing.project_context=true` 不得静默继续。同时按 `spec.enabled` 决定是否读取 `project-knowledge/specs/`

## 执行

<workflow skill="quality-control" version="2">

<step n="1" goal="组装质量框架">
 - 列出本轮质量检查覆盖的 AC、Requirement / Scenario、任务项、变更文件、证据和审查员结果
 - 标注哪些材料缺失；缺失材料不能被自述替代
 - 「应到材料」清单不得自由清点，须绑定权威来源：取当前 stage contract 的 `inputs[].required` 项，或 `harness control context-index`（同 `harness context check` 机制）返回的 required artifact 列表，逐项核对实际存在性。缺失项一律登记为 `inputs_missing.*`（与 `harness context check` 同口径标记），而非凭印象判断"材料够不够"。
</step>

<step n="2" goal="运行程序化检查">
 - 对可用阶段产物运行 `stage-gate/scripts/check_contracts.py`
 - 对当前项目运行 `verify/scripts/collect_command_evidence.py`，或记录命令 unavailable
 - 对 runtime 资产质量任务运行 `harness-lint/scripts/check_runtime_consistency.py`
</step>

<step n="3" goal="语义审查">
 - 根据材料选择 `code-review`、`verify`、或对应审查员 Agent 处理需求完整性、架构、安全、测试充分性和风险判断
 - 若审查员 HOLD，保留原始 finding，禁止直接降级为建议
</step>

<step n="4" goal="分类 Findings">
 - 按协议分为 Hard Gate、Soft Gate、Observation
 - 每个 finding 写明 evidence、上游约束、影响、建议处理方式
</step>

<step n="5" goal="修复闭环">
 - 条件：存在 Hard Gate
 - 返回对应 carrier 修复：文档问题回上游 stage，代码问题回执行 / receiving-review，证据问题回验证，runtime drift 回 Harness 自检修复
 - 修复后重跑相关程序化检查和审查员
 - 条件：Soft Gate 需要接受风险
 - 触发 Decision Gate，记录 accepted risk 后才能继续
</step>

<step n="6" goal="记忆决策">
 - 判断发现是否需要写入 project-context、project-knowledge/specs、测试模板、审查检查清单或 future runtime candidate
 - 为每个记忆决策分配 `MEM-NNN` 候选 ID；retrospective 阶段负责合并去重并写入 Memory Update Contract（记忆更新契约）
 - 每项给出 applied / proposed / 延后和理由
</step>

</workflow>
