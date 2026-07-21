# 任务契约

## 这是什么

任务契约是 HarnessV2 模板中每轮任务的入口契约。

AI 接到一个任务后，第一件事不是开始写代码，而是先形成一份任务契约。这份契约回答：

- 这次要做什么
- 用户是谁、遇到什么问题、在哪个场景需要它、价值和成功指标是什么
- 边界在哪
- 什么算完成
- AI 可以自己推进到什么程度
- 什么时候必须停下来找人

没有任务契约，AI 不知道自己被授权做什么。有了任务契约，AI 才能围绕它持续推进，而不是每走一步都要问人。

## 为什么需要它

在旧 Harness 中，任务的目标、边界、验收散落在 prd、solution、tech、任务项、状态之间，没有被收束为一个运行时第一对象。结果是：AI 知道自己处在哪个阶段，但不一定清楚这次任务应该按什么治理强度推进。

任务契约解决这个问题：把所有控制信息收束成一个对象，让 AI 在整个执行过程中都能回头查阅。

## 字段定义

一份任务契约至少包含以下字段：

### objective

一句话说明这次任务要达成什么。

### user_stories

用户故事不是只写“角色 / 目标 / 价值”。每条故事必须带产品故事上下文：

- `user`：具体用户、用户分层或角色
- `problem`：用户遇到的问题、痛点或当前失败状态
- `scenario`：触发场景、使用上下文或关键动作
- `value`：为什么这件事有价值
- `success_metrics`：至少一条可观察成功信号和目标

缺少这些字段时，PRD 会被迫自行发明用户场景，任务契约审查应 HOLD。

### scope_in

明确纳入本轮的工作内容。

### scope_out

明确不做的内容，每条附理由。

### acceptance_criteria

可验证的验收标准。优先使用 Given / When / Then 格式。

### autonomy_level

机器字段名保留 `autonomy_level`，正文展示为“执行治理级别”。三选一：

- 快速执行：治理风险低、边界清晰、局部可逆、自动验证充分；允许跳过 `execution_governance.levels.快速执行.skippable_stages` 中配置的阶段，实际执行的阶段仍需通过 Gate
- 专家确认：存在中等技术或验证风险，但不需要人做业务 / 安全 / 风险接受决策；阶段专业 reviewer PASS + Stage Gate PASS 通常即可继续，只有 `human_checkpoints` 配置的阶段暂停给人确认
- 受控推进：存在高治理风险、不可由 AI 单独承担的决策、不可逆影响、关键数据 / 权限 / 外部依赖 / Agent 行动权变化，或自动验证不足；默认不跳过阶段，必须人工确认的阶段由 `execution_governance.levels.受控推进.human_checkpoints` 配置

历史任务或旧模板中的 `A1` / `A2` / `A3` 不再作为正式值保存。接入或恢复时必须先按 `execution_governance.legacy_level_aliases` 迁移到新治理级别。

### governance_assessment

治理级别必须由结构化风险评估支撑，而不是只看文件数、角色数或模块数。任务接入阶段应写入：

- `hard_triggers[]`：权限、认证、安全、隐私、支付、数据删除 / 迁移、新外部服务、Agent 行动权扩大、验证不足等硬触发。命中任一项通常直接进入 `受控推进`。
- `dimensions{}`：决策权、可逆性、影响面、验证可靠性、数据 / 权限、外部依赖、Agent 行动权、不确定性，每项标记 `low / medium / high` 和理由。
- `scale_signals{}`：文件数、用户角色数、模块跨度等辅助信号。它们可以提高治理级别，但不能用来降低 hard trigger 或核心风险。
- `decision_rule`：说明为什么得到当前 `autonomy_level`。
- `user_confirmation_required`：治理判定必须在任务契约确认时展示给用户；降低治理级别或删除 checkpoint 必须记录 approval。

### required_checkpoints

列出本 mission 最终决定哪些阶段文档完成后需要人确认才能继续。默认从 `harness-runtime/config/harness.yaml` 的 `execution_governance.levels.<autonomy_level>.human_checkpoints` 派生；任务契约可以基于任务风险做显式覆盖。例如：

```yaml
required_checkpoints:
 - prd
 - solution
 - tech_design
```

未列入的阶段文档默认不需要人确认，AI 可以自主通过。

### escalation_rules

定义什么条件下 AI 必须暂停并升级给人。例如：

```yaml
escalation_rules:
 - trigger: scope_change
 action: pause_and_ask
 - trigger: high_risk_change
 action: pause_and_ask
 - trigger: multi_option_tradeoff
 action: present_options
```

### constraints

本轮的硬约束。例如不能改哪些接口、必须兼容哪些版本、不能引入哪些依赖。

### delivery_expectation

交付时需要包含什么。例如：代码变更 + 测试 + 验证报告 + 交付总结。

## 什么时候创建

- **autonomous_execution**：默认执行模式。AI 收到明确任务后自动创建，写入 `harness-runtime/harness/missions/`
- **governed_execution**：高治理执行模式。AI 创建草稿，等人确认后生效
- **conversation**：讨论模式。不创建

## 什么时候更新

任务契约在整个任务生命周期中可能被更新，但更新必须留痕：

- 发现范围需要调整时
- 人工审核后修改验收标准时
- 升级条件被触发后

更新不是覆盖原文，而是在文档末尾追加变更记录。

## 文件位置

`harness-runtime/harness/missions/<mission-id>/mission-contract.md`

其中 `<mission-id>` 建议使用日期 + 简短描述，例如 `20260322-user-auth`。

## 与 BMAD 的关系

BMAD 没有任务契约这个显式对象。它的控制信息分布在 PRD、architecture、story 等多个文件中。HarnessV2 把这些控制信息收束成一个运行时入口对象，让 AI 不需要在多个文件之间拼凑自己的授权范围。

## 模板

参见 `harness-runtime/templates/mission-contract.md`。
