# Artifact Gate

每次技能产出当前 Mission Slice 的 stage artifact 后，必须经过 Gate 检查和 Work Graph operation，才能推进到下一项 Board / Mission Slice 工作。

## 强制约束

以下情况 **禁止推进 Work Graph**：

1. 阶段文档不存在
2. 阶段文档是空文件或只含模板占位符
3. 文档缺少当前阶段的必填章节（见下方最小结构要求）
4. 产出内容与上游文档存在直接矛盾（如 AC 编号错误、范围超出 scope_in）

## 各文档最小结构要求

| 文档 | 必须包含 |
|------|---------|
| `mission-contract.md` | objective、scope_in、scope_out、acceptance_criteria、autonomy_level（执行治理级别） |
| `discovery-brief.md` | TL;DR、问题空间、影响面、关键发现、风险与未知、产品定义 输入建议、证据索引 |
| `product/product-definition.md` | TL;DR、背景与问题定义、目标与范围、关键需求、验收口径 |
| solution.md | 问题回顾、目标驱动设计、关键决策（如有）、适配性评估、所选路线与理由、影响面、风险 |
| interaction.md | 核心流程、关键状态、异常场景 |
| tech-design.md | 改动概述、模块级计划、接口变化、验证策略、生产就绪要求 |
| execution-brief.md | 任务目标、关键约束、任务项、每个任务项的完成边界、实现要点、已知风险 |
| 差量规格（`harness-runtime/harness/stages/<id>/specs/<capability>/spec.md`，仅 `spec.enabled=true`） | 头部 `Mission` + `Capability` + `Baseline` 标识；至少一个非空的 Requirement 块（`## ADDED / MODIFIED / REMOVED Requirements` 任一）；每个 Requirement 至少一个 `#### Scenario` 且包含 `**WHEN**` 与 `**THEN**`；MODIFIED 块必须写完整新版（不只写差异） |
| code-review.md | 评审摘要、发现列表（High/Med/Low）、正确性、TDD 有效性、设计一致性、安全与可靠性、评审结论 |
| `verification-report.md` | 验证目标、验证方法、验证结果、遗留问题 |
| `acceptance-result.md` | 交付入口、你要验收什么、结果验收清单、关键结果证据、未满足/无法验收、验收决定 |
| `delivery-package.md` | 交付摘要、验收状态、证据链接、遗留项、下一步建议 |
| retrospective.md | 执行摘要、做得好的、发现的问题、根因分析、改进行动、更新 project-context.md |

## Gate 执行

Gate 检查由 `stage-gate` 技能执行（机械化逐项验证）。自治循环在每次技能完成后调度它。

本规则是 Gate 的 **约束声明**，Stage Gate 技能是 Gate 的 **执行实现**。

## 自修复原则

发现 Gate 不通过时：

1. 优先自行修复（补充缺失章节、修正占位内容）
2. 修复后重新过 Gate
3. 修复 3 次仍失败 → 发起 Decision Gate，不继续盲目推进
