# 质量控制协议

质量控制协议治理需求对齐、文档质量、代码质量、测试充分性、运行时证据和记忆决策。它不替代 `code-review` 或 `verify`，而是协调确定性证据和审查员的语义判断。

## 触发条件

当用户要求质量评估、Stage Gate 报告 evidence 缺口、验证无法支撑验收场景结论、审查员返回 HOLD，或 retrospective 中出现重复质量缺口时，使用本协议。

## 控制平面绑定

| 平面 | Runtime 职责 |
|------|--------------|
| Intent | 读取任务验收场景、范围、质量与运行约束、执行治理级别和 Checkpoint |
| 上下文 | 读取 project-context、project-knowledge/specs、历史质量缺口和命令约定 |
| Guide | 应用规则、阶段工作流、solution / tech-design 约束和禁止捷径 |
| Action | 构建追溯矩阵、运行命令证据、触发审查员、生成修复动作 |
| Feedback | 记录 hard / soft / observation finding 及其证据引用 |
| Regulation | 决定继续、修复、暂停或升级 |
| Memory | 决定是否更新 project-context、project-knowledge/specs、模板或审查检查清单 |

## 流程

1. 从任务契约、PRD / 差量规格、设计文档、execution-brief、变更文件、命令证据、审查员结果和 project-context组装质量 Frame。
2. 构建追溯矩阵：`验收场景 -> 需求/场景 -> 设计约束 -> Task -> 变更文件 -> 测试/证据 -> Review/Verify 结果`。
3. 先运行确定性检查：contract checker、command evidence collector，以及可用的 build / typecheck / lint / test / E2E / security / dependency 检查。
4. 通过合适的审查员或工作流运行语义检查：correctness、architecture、security、E2E、Agent behavior、document adversary 或验证 interpretation。
5. 将 findings 分类为 Hard Gate、Soft Gate 或 Observation。
6. 修复 Hard Gate finding 和被选中的 Soft Gate finding，然后重跑相关确定性检查和审查员。
 审查员 HOLD 必须映射到审查证据契约的 `findings[*].status`：open → fixed / accepted_risk；不得只在正文中说明。
7. 形成 Memory Decision：applied、proposed 或延后，并写明目标和理由。

## 程序化控制

- `stage-gate/scripts/check_contracts.py` 校验控制契约是否存在、必填字段、引用、阻塞状态，以及可确定判断的证据语义。
- `verify/scripts/collect_command_evidence.py` 记录 test、lint、typecheck、build 和可用 security 检查的最新命令证据。
- `harness-lint/scripts/check_runtime_consistency.py` 检查模板、工作流、协议 和 scripts 之间的 runtime asset drift。

## 推理控制

AI / 审查员判断负责需求充分性、质量分类、架构风险、安全影响、超越覆盖率数字的测试充分性，以及风险是否可以接受。

## 证据

Hard Gate 必须有具体证据引用。没有证据的验收场景 pass 无效。工具不可用是 verification 缺口，不是 pass。

## 禁止捷径

- 不得用自述替代命令输出或审查员结果。
- 不检查验收场景 / requirement / 任务项 / test 链路时，不得判断代码质量。
- 不得把覆盖率百分比当作充分性证明。
- 不得为了通过 Quality Gate 而弱化或删除测试。
- 没有修复、accepted risk 或 Decision Gate 时，不得越过审查员 HOLD 继续推进。
- **轮次永不放行**（见 `core.md`「严格审查不变量」）：审查轮次只记录修复历史，达到任何轮次都不会自动放行或降级通过；"都第几轮了 / 暂时够用 / 后续会补"不是越过 HOLD 的理由。修复循环只在审查员于等同严格度下 PASS 时退出；卡死时发起 Decision Gate（候选不含"接受遗留 / 降级通过"），残留风险只能由用户显式拥有并记 approval。

## 升级条件

当修复扩大任务范围、改变架构边界、增加依赖、留下未解决的 Hard Gate、与命令证据冲突，或需要用户接受质量风险时，必须升级。

## 记忆更新

重复出现的缺口会成为 project-context、project-knowledge/specs、测试模板、审查员检查清单或未来 runtime 变更的候选项。defer 决策必须包含理由。
