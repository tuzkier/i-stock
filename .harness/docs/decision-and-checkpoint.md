# 决策系统与 Checkpoint

## 这是什么

这份文档定义了 HarnessV2 模板中"AI 什么时候必须停下来找人"的完整机制。

核心问题只有一个：AI 在持续执行的过程中，什么时候应该暂停，以什么方式暂停，人回来后如何恢复。

## 两种暂停机制

HarnessV2 把"需要人参与"拆成两种独立的机制：

### Checkpoint（阶段文档确认）

**含义**：某份阶段文档写完了，需要人看一眼确认后才能继续。

**特点**：
- 可预测的、按配置触发
- 在任务契约的 `required_checkpoints` 中声明
- AI 知道什么时候会遇到 Checkpoint
- 人确认后 AI 继续推进

**例子**：
- product/product-definition.md 写完了，需要人确认需求理解是否正确
- solution.md 写完了，需要人确认方案选择
- tech-design.md 写完了，需要人确认技术路径

### Decision Gate（决策请求）

**含义**：AI 在执行过程中遇到了自己无法或不应该单独做的决定，需要人来拍板。

**特点**：
- 不完全可预测，由执行过程中的实际情况触发
- 在任务契约的 `escalation_rules` 中定义触发条件
- AI 需要清晰描述问题、选项和建议
- 人拍板后 AI 按决定继续

**例子**：
- 发现需求范围比预期大，需要确认是否扩展
- 有两个技术方案各有利弊，需要人选
- 改动涉及线上数据，需要人授权

## 四种决策类型

所有 Decision Gate 归为四类：

### 1. boundary_decision

**触发**：需求边界变了，或者边界不清楚。

**AI 应该做什么**：
- 描述当前理解的边界
- 描述发现的偏差或歧义
- 给出建议的边界调整
- 说明如果不调整会怎样

### 2. artifact_confirmation

**触发**：这是 Checkpoint 的实现方式。某份阶段文档需要人确认。

**AI 应该做什么**：
- 展示完成的文档
- 简要说明关键决策点
- 明确需要人确认什么

### 3. risk_acceptance

**触发**：执行涉及高风险操作。

**AI 应该做什么**：
- 描述风险是什么
- 描述影响范围
- 描述缓解措施
- 说明如果不做这个操作会怎样

### 4. tradeoff_decision

**触发**：存在多个可行方案，需要人选择。

**AI 应该做什么**：
- 列出候选方案（2-3 个）
- 每个方案的利弊
- 给出推荐方案和理由
- 说明如果选错的代价

## 决策请求的结构

每个 Decision Gate 触发时，AI 应该产出一个结构化的决策请求：

```
类型：boundary_decision / artifact_confirmation / risk_acceptance / tradeoff_decision
问题：一句话描述需要人做什么决定
背景：为什么现在需要这个决定
选项：
 - 选项 A：描述 + 利弊
 - 选项 B：描述 + 利弊
推荐：AI 建议选哪个，为什么
如果继续不等：会有什么风险
如果等待：会延迟什么
```

## Approval Record

人做出决定后，AI 需要记录到 `harness-runtime/harness/state/approvals.json`：

```json
[
 {
 "mission_id": "20260322-user-auth",
 "type": "artifact_confirmation",
 "stage": "prd",
 "status": "approved",
 "decided_at": "2026-03-22T16:10:00+08:00",
 "comment": "需求理解正确，可以继续"
 }
]
```

不再允许从 markdown 文案中猜测审批状态。所有审批都以结构化记录为准。

## 恢复规则

人做完决定后，AI 如何恢复执行：

1. AI 读取 `approvals.json` 中的最新记录
2. 根据决策类型和结果，更新任务契约（如有变更）
3. 回到自治循环的"恢复上下文"步骤
4. 继续推进

## Checkpoint 的默认配置

哪些阶段文档默认需要人确认，定义在 `harness-runtime/config/harness.yaml` 的 `execution_governance.levels.<autonomy_level>.human_checkpoints` 字段中。用户可以按项目需求调整。旧 `A1` / `A2` / `A3` 只通过 `execution_governance.legacy_level_aliases` 映射到新治理级别；运行时不再读取旧 `checkpoints` 字段。

治理级别本身也是授权决策：Intake 阶段必须把建议的 `autonomy_level`、hard triggers、治理风险维度和 `required_checkpoints` 展示给用户确认。AI 可以建议治理级别，但用户确认后才进入自治循环。若用户要求降低治理级别、删除 checkpoint 或接受未解决风险，必须写入 `approvals.json`，类型使用 `risk_acceptance` 或 `tradeoff_decision`。

默认治理级别：

| 执行治理级别 | 可跳过阶段 | 人工确认点 |
|--------------|------------|------------|
| 快速执行 | `discovery`、dependency-impact evidence carrier、`solution`、`interaction` | `acceptance_result` |
| 专家确认 | `discovery`、`interaction` | `acceptance_result` |
| 受控推进 | 无 | `prd`、`solution`、`tech_design`、`execution_brief`、`verification_report`、`acceptance_result`、`delivery_package` |

## 与 BMAD 的关系

BMAD 通过命令编排隐式实现了 Checkpoint：每个工作流结束后会提示"Next Steps"，人工触发下一个工作流。这本质上是人工 Checkpoint，但没有显式建模。

HarnessV2 把 Checkpoint 和 Decision Gate 做成了显式机制，这样 AI 可以在不命中 Checkpoint 的阶段自动通过，而不需要人反复手动触发。

## 与旧 Harness 的关系

旧 Harness 有 `decision_queue` 和 `ask_human`，方向是对的。但没有定义清楚四种决策类型、没有结构化的决策请求格式、没有 `approvals.json`。HarnessV2 把这些补齐。

旧 Harness 的 `stage-gate` 混合了 Gate 判定、决策请求、执行编排。HarnessV2 把它拆成三个独立系统：Artifact Gate（Gate）、决策系统（决策）、Execution Driver（驱动）。
