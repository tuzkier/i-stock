---
name: delivery
description: '当 code-review 通过且验证完成、准备打包交付时使用。当用户说"交付""提交成果""生成交付物"时也触发。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# 交付 — 交付

## 概述

将已验证的成果整理为面向人的验收结果，并生成内部归档交付包。

## 阶段能力

delivery 对应 RUP 移交阶段和部署工作流。它要证明：已验证增量有清楚交付边界、用户可独立执行的验收路径、真实结果证据、透明风险披露、使用 / 部署就绪说明和用户验收检查点；不得把未验证范围、测试通过或聊天说明包装成已交付。

## 何时使用

- code-review 通过且验证完成
- 用户说"交付"、"打包"、"提交成果"

## 何时不使用

- 验证还未通过（→ 先完成验证）

## 快速参考

| 步骤 | 产出 |
|------|------|
| 读取验证结果 | 确认状态 |
| 生成 `acceptance-result.md` | 用户可验收结果 |
| 生成 `delivery-package.md` | 内部交付归档 |
| PR 或合并 | 代码入库 |
| 通知用户 | 交付完成 |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#delivery`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Delivered Scope | User acceptance | 用户不知道验收范围 |
| Acceptance Item | User | 交付包不可自验 |
| How To Verify | User | 只能相信 Agent 口头说明 |
| Known Gap / Risk | User / Retrospective | 风险被隐藏 |
| Evidence Link | Audit | 交付不可追溯 |

按 `workflow.md` 执行详细步骤。
# 交付工作流

> **方法论参考**:`.harness/docs/methodology-reference.md` §14(文档结构框架(Diátaxis Framework);架构决策记录(ADRs))§15(十二要素应用(12-Factor App);配置即代码(GitOps);渐进式交付(Progressive Delivery))§16(站点可靠性工程(SRE);服务水平目标 / 指标(SLO / SLI);可观测性三支柱(Three Pillars of Observability);开放遥测(OpenTelemetry))

所有命令行接口(CLI)调用通过 `harness-cli` 技能(`--json` 模式)。

<workflow stage="delivery" version="2">

<goal>
  产出两类交付物:面向用户验收的验收结果(acceptance-result.md,证明结果是否正确),与内部归档追溯的交付包(delivery-package.md,记录过程和交付边界);并取得用户验收检查点(checkpoint)。
</goal>

<role>
  你是交付整理者。你把「做完了」转化为「用户能验收什么、怎么验收、实际结果是什么、哪些限制仍然存在」。你不发明内容,只从验证报告的结果证据(result_evidence)、任务契约验收条件、验收场景和实际可访问入口中汇总。不把未验证通过的内容算作交付,不把测试命令通过当成用户验收。
</role>

<stage_capability>

交付阶段对应 RUP 移交阶段(Transition)和部署工作流(Deployment)。它的核心能力不是“写完成总结”,而是回答“已验证增量是否具备被用户接收、独立验收和后续维护的条件”。

| 能力 | 本阶段必须判断什么 | 失败时 |
|---|---|---|
| 输入合格性判断 | 任务契约、执行简报、代码审查、验证报告、验收场景 / 条件结果证据和交付入口是否齐全 | BLOCKED,回 verify / execute / code-review 补齐 |
| 验证结论承接判断 | verification-report 中每条验收场景 / 条件是否在交付包中有明确归宿:通过、deferred 或 returned | HOLD,不得静默遗漏 |
| 交付边界判断 | 已交付、未交付、范围外、延后事项是否从上游和实际差异中区分清楚 | HOLD,不得扩写交付范围 |
| 用户验收路径判断 | acceptance-result 是否让用户知道入口、环境、输入、步骤、预期结果、实际结果、失败判定和证据路径 | HOLD,不得请求验收 |
| 使用就绪判断 | 运行入口、环境前提、配置、账号 / 权限、数据准备、迁移影响、回滚 / 恢复和可观测性是否足以接收 | BLOCKED 或 accepted risk |
| 风险披露判断 | 未通过、未验证、部分满足、范围外、已接受风险和后续项是否写清用户后果和处理建议 | HOLD 或 Decision Gate |
| 验收包自包含判断 | acceptance-result 和 delivery-package 是否脱离聊天记录、源码差异和未引用日志也能成立 | HOLD,补交付说明 |
| 用户检查点判断 | 是否向用户展示验收摘要并取得接受 / 继续修复 / 接受风险后交付的检查点 | 不得完成 delivery |
| 移交暂停判断 | delivery 完成后是否暂停,等待用户或看板明确触发复盘 / 分支收尾 | 不得自动进入后续阶段 |

</stage_capability>

<method>

交付阶段采用 RUP 的移交阶段(Transition)和部署工作流(Deployment)口径。交付不是重新验证,也不是写总结,而是判断已验证增量是否具备被用户接收、独立验收和后续维护的条件。

具体方法按七步执行:

1. **输入合格检查**:确认任务契约、执行简报、代码审查、验证报告和实际产物齐全。缺少验收场景 / 条件来源、结果证据、交付入口或用户可执行步骤时,停止交付并回到对应上游阶段补齐。
2. **交付边界判定**:从任务契约、执行简报和实际差异中区分已交付范围、未交付范围、范围外事项和延后事项。不得把局部通过的能力扩写成完整需求交付。
3. **验收路径转译**:把验证阶段的工程证据转成用户可执行验收步骤。每条验收场景 / 条件必须有入口、环境前提、操作步骤、输入、预期结果、实际结果、失败判定和证据路径。
4. **结果证据审查**:每条通过的验收场景 / 条件必须由用户可观察结果或等价证据支撑。只含命令退出码、缺少实际观察结果或无法关联验收场景 / 条件的证据,不得支撑通过结论。
5. **部署与使用就绪判断**:确认交付入口、运行前提、配置要求、账号 / 权限、数据准备、迁移影响、回滚 / 恢复说明是否足以让用户接收本次增量。缺少关键使用前提时,不请求验收。
6. **残留风险披露**：把失败项、未验证项、已知缺口、范围外事项和已接受风险写成用户能理解的后果、影响范围和建议处理方式。不得用"后续优化"掩盖阻断风险。
6b. **未验证项处理**：验证报告中标记为未通过或未验证的验收场景 / 条件必须在交付包中明确处理——要么标记为 `deferred`（延后到后续 Slice 并说明原因和影响），要么标记为 `returned`（回流到 verify / execute 并说明回流原因）。不得静默忽略或用"后续优化"掩盖。验证报告中的每条验收场景 / 条件在交付包中必须有明确归宿：通过、deferred 或 returned。
7. **移交说明形成**:验收结果面向用户,交付包面向归档和维护者。两份产物必须自包含,不能要求用户回看聊天记录、源码差异或未引用日志才能完成验收。

</method>

<invariants>

| 标识 | 检查 | 执行方式 |
|---|---|---|
| `delivery-contract-via-cli` | 交付包契约(delivery-package.contract.yaml)和验收结果契约(acceptance-result.contract.yaml)不得被 Agent 直接写入或编辑,必须经 Harness 命令行接口 | hook=delivery-check-contract-via-cli |
| `acceptance-result-human-facing` | 验收结果(acceptance-result.md)面向人类读者,不暴露内部流水账,不内嵌围栏式 YAML 契约 | hook=harness-lint |
| `pass-ac-needs-result-evidence` | 任一通过的验收场景 / 条件缺少结果证据(result_evidence)或复现步骤时,不得请求用户验收 | hard_gate=acceptance-evidence-complete |
| `reviewer-readonly` | 验收包审查员(acceptance-package-reviewer)必须以只读子 Agent 调用 | registry=subagents/acceptance-package-reviewer[readonly=true] |
| `delivery-pauses` | 交付完成后暂停,不自动调度复盘(retrospective)或分支收尾(finishing-branch) | hook=harness delivery handoff --pause |

</invariants>

<entry>
  - 验证阶段已完成,验证报告(verification-report)已证明当前增量结果。
  - 交付阶段只消费已实现、已审查、已验证的事实;如果验证证据不足,回到验证阶段。
</entry>

<exit>
  - `acceptance-result-written`: 验收结果(acceptance-result.md)已写入交付阶段目录,每个通过的验收场景 / 条件都有预期结果、实际结果、复现步骤和结果证据。
  - `delivery-package-written`: 交付包(delivery-package.md)已写入交付阶段目录,包含交付边界、证据索引、残留风险和移交说明。
  - `contracts-filled`: 交付包和验收结果的契约已填充,且 `harness contract check` 通过。
  - `user-accepted`: 审批记录包含验收结果检查点。
  - `handoff-pause`: `harness delivery handoff --pause` 已写入移交证据。
</exit>

<subagents>

| 角色 | 模式 | 范围 / 限制 | 角色包 |
|---|---|---|---|
| `release-readiness-expert` | spawn | harness-runtime/harness/artifacts/${mission-id}/delivery/delivery-package.md, harness-runtime/harness/artifacts/${mission-id}/delivery/acceptance-result.md | `.harness/common/agents/release-readiness-expert.md` |
| `acceptance-package-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/acceptance-package-reviewer.md` |

</subagents>

<inputs>

| 输入 | 必需 | 用途 |
|---|---|---|
| `mission-contract.md` | 是 | 读取原始目标、范围、非目标、成功定义和验收条件 |
| `execution-brief.md` | 是 | 读取授权范围、已完成任务和必需证据 |
| `code-review.md` | 条件必需:代码审查已完成时读取 | 读取审查结论、已解决问题和可接受风险 |
| `verification-report.md` | 是 | 读取验收场景 / 条件结果、命令证据、结果证据、未验证项 |
| `harness.yaml` | 是,通过配置快照读取 | 读取项目交付约束 |

</inputs>

<outputs>

| 产物 | 路径 | 类型 | 校验 |
|---|---|---|---|
| `acceptance-result-md` | `harness-runtime/harness/artifacts/${mission-id}/delivery/acceptance-result.md` | Markdown | 用户验收产物 |
| `delivery-package-md` | `harness-runtime/harness/artifacts/${mission-id}/delivery/delivery-package.md` | Markdown | 内部归档产物 |
| `delivery-package-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/delivery-package.contract.yaml` | 契约 | `harness contract check` |
| `acceptance-result-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/acceptance-result.contract.yaml` | 契约 | `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化">
 - 读取任务契约、执行简报、代码审查和验证报告。
 - 调用命令行接口 `harness mission stage start` `--mission ${mission-id} --stage delivery`,证据为必需。
 - 调用命令行接口 `harness trace log-init` `--mission ${mission-id}`,证据为必需。
 - 调用命令行接口 `harness frame current` `--mission ${mission-id}`,证据为必需。
 - 调用命令行接口 `harness delivery summarize` `--mission ${mission-id}`,证据为必需。
 - 执行输入合格检查:确认任务契约中有可验收目标,验证报告中有每个验收场景 / 条件的结果,且至少有一个用户可访问或可执行的交付入口。任一缺失时停止交付,回到对应上游阶段。
</step>

<step id="step-1" n="1" goal="专业角色调度">
 <dispatch role="release-readiness-expert" mode="spawn" />
 - 任务信封:验证证据路径、代码审查发现路径、验收场景 / 条件追踪、已知风险、审批记录、写入范围、完成条件和风险边界要求。
 <dispatch role="acceptance-package-reviewer" mode="spawn" />
 - 交付物生成后调度审查员,任务信封包含:验收结果路径、交付包路径、验收证据索引、只读约束和结论输出格式。Markdown 只保留面向人的交付审查摘要。
</step>

<step id="step-2" n="2" goal="汇总交付内容与结果证据">
 - 从执行简报提取完成的任务项列表和变更文件清单;从验证报告提取验收场景 / 条件通过 / 未通过状态、命令证据(command_evidence)和结果证据(result_evidence);从代码审查提取评审结论和修复记录。
 - 组织交付摘要:一句话概括(做了什么 / 达到什么效果)、变更范围(新增 / 修改 / 删除文件数与关键模块)、实现方式(从方案和技术设计提取关键技术决策)、交付入口(用户可访问地址(URL)、接口(API)、命令行(CLI)、测试账号、测试数据、分支或提交)。
 - 判定交付边界:列出已交付、未交付、范围外、延后四类事项,并说明每类事项的来源。范围外和延后事项不得写成已交付能力。
</step>

<step id="step-3" n="3" goal="生成面向人的 acceptance-result.md">
 - 逐条列出任务契约和验收场景中的验收条件:编号、原要求、预期结果、实际观察结果、复现步骤、结果证据和结论。使用 `harness-runtime/templates/acceptance-result.md` 模板结构,写入 `harness-runtime/harness/stages/<mission-id>/acceptance-result.md`。场景 / 条件 ID 仅作为追溯锚点。
 - 验收结果必须面向人类读者,不暴露内部流水账,包含交付入口、验收清单、关键结果证据、无法验收场景 / 条件和验收决定。
 - 每条验收步骤必须包含:环境前提、入口、输入、操作步骤、期望结果、失败判定和证据路径。
 - 硬性检查 `acceptance-evidence-complete`:任一通过的验收场景 / 条件缺少结果证据或复现步骤时,停止交付,不能请求用户验收,返回验证阶段补齐实际结果证据。
</step>

<step id="step-4" n="4" goal="遗留项和后续">
 - 从以下来源收集遗留项:验证报告未通过或未覆盖的验收场景 / 条件、代码审查标记为低严重级别的改进建议、执行简报标注且实现中被证实的风险、实现过程发现的新需求或改进机会。
 - 对每个遗留项给出:描述、来源、影响范围、用户后果、严重性(必须处理 / 建议处理 / 可忽略)和建议处理方式。
 - 对残留风险进行披露判断:若风险会影响用户验收、数据安全、权限、兼容性、迁移或回滚,必须写入验收结果和交付包;没有用户接受风险或决策记录时,不得把它降级为建议。
</step>

<step id="step-5" n="5" goal="生成 delivery-package.md">
 - 使用 `harness-runtime/templates/delivery-package.md` 模板结构,填充:填写方法、交付摘要、交付边界、部署 / 使用就绪检查、验收状态、证据链接、残留风险与遗留项、移交说明、下一步建议。
 - 验收状态只引用验收结果(acceptance-result.md),不重复作为用户验收物。证据链接必须指向验收结果、验证报告、代码审查和关键结果证据。
 - 写入 `harness-runtime/harness/stages/<mission-id>/delivery-package.md`。
 - 若 `contracts/delivery-package.contract.yaml` / `contracts/acceptance-result.contract.yaml` 不存在,调用 `harness contract init` 初始化;若已存在只能通过补丁命令更新。两份 Markdown 的「控制契约」段只保留 `Contract:` 引用,禁止追加围栏式 YAML 契约。
</step>

<step id="step-6" n="6" goal="后续事项归类与移交">
 - 确认交付包是内部归档产物,验收结果是用户验收产物;两者不能互相替代。
 - 若所有验收场景 / 条件通过且没有阻断性遗留项,交付文档声明当前增量可请求用户验收。
 - 若存在必须后续处理的遗留项,交付文档必须把它归类为阻断性、建议性或可忽略,并说明用户影响和建议处理方式。
 - 若存在阻断性遗留项且用户未接受风险,不得把当前增量写成完成;应返回修复、补验证或发起用户决策。
</step>

<step id="step-7" n="7" goal="最终验收 Checkpoint">
 - 无论验收场景 / 条件是否全部通过,都必须向用户展示验收结果摘要和交付入口。验收请求明确列出:一句话摘要、交付入口、验收场景 / 条件预期结果 / 实际结果摘要、关键结果证据、阻断性遗留项和建议性遗留项。
 - 调用 tool: `AskUserQuestion`。
  - 问题:本次交付的验收请求,请确认
  - 候选答案:
     - 接受交付
     - 继续修复
     - 接受风险后交付(accepted_risk,需风险摘要(risk_summary))
 - 条件:用户接受交付或接受风险后交付
  - 调用命令行接口 `harness approval append` `--mission ${mission-id} --type checkpoint --stage acceptance-result --status approved`,证据为必需。
  - 更新 mission-status:checkpoints_passed 追加 acceptance-result。
 - 条件:用户要求继续修复
  - 根据用户反馈路由到接收审查反馈(receiving-review)/ 执行 / 缺陷修复(bug-fix),修复后重新验证和交付。
</step>

<step id="step-8" n="8" goal="Artifact Gate 自检">
 - 验证验收结果包含最小必要结构:填写方法、交付入口、你要验收什么、结果验收清单、关键结果证据、未满足 / 无法验收、验收决定;每个通过的验收场景 / 条件有预期结果、实际结果、复现步骤和结果证据。
 - 验证交付包包含最小必要结构:填写方法、交付摘要、交付边界、部署 / 使用就绪检查、验收状态、证据链接、残留风险与遗留项、移交说明、下一步建议、轻量交付指标(DORA)信号(交付周期、返工次数、审查暂停次数、验证失败次数、回滚 / 后续任务次数)。验证最终验收已记录到审批记录;未记录时不得把任务状态置为完成。
 - 调用命令行接口 `harness contract check` `--artifact harness-runtime/harness/stages/${mission-id}/delivery-package.md`,证据为必需。
 - 调用命令行接口 `harness gate transition` `--stage delivery --mission ${mission-id} --mission-slice harness-runtime/harness/work-graph/mission-slices/${mission-id}.yaml --artifact harness-runtime/harness/stages/${mission-id}/delivery-package.md --contract-artifact harness-runtime/harness/stages/${mission-id}/contracts/delivery-package.contract.yaml --json`,证据为必需。
 - 条件:gate status != PASS
  - 按 failed_checks 修复 delivery-package.md、acceptance-result.md、审批记录或 contract 后重新运行 gate;不得 handoff 或完成阶段。
 - 条件:结构不完整
  - 自行补充缺失部分,不要跳过。
</step>

<step id="step-9" n="9" goal="任务收尾 + handoff">
 - 调用命令行接口 `harness delivery compute-conclusion` `--mission ${mission-id}`,证据为必需。
 - 得到类型化结论(delivered / continue_fix / blocked)。
 - 条件:结论为 delivered(所有验收场景 / 条件通过且无阻断性遗留项,第 7 步已取得用户验收,第 8 步 Gate transition 已 PASS)
  - 调用命令行接口 `harness delivery handoff` `--mission ${mission-id} --pause`,证据为必需。
  - 阶段完成、Gate 报告、Work Graph operation、下一 Mission Slice 已由 `gate transition` 写入；不得再单独调用 `mission stage complete` / `gate advance` / `board select`。
  - 交付到此暂停。不自动调度复盘(retrospective)或分支收尾(finishing-branch);入口由用户或看板在下一轮明确触发。
 - 条件:结论为 delivered,但存在阻断性遗留项且用户在第 7 步接受风险后交付,且第 8 步 Gate 已 PASS
  - `harness delivery handoff --pause` 时记录已接受风险摘要(引用审批编号),再执行阶段完成。交付以接受风险关闭并暂停,不自动调度复盘。
 - 条件:结论为 continue_fix 或 blocked
  - 不得完成阶段;按失败路径路由继续修复或发起决策门(Decision Gate)。
</step>

<step id="step-10" n="10" goal="条件:交付包加入 Agent 能力产物">
 - 条件:agent_engineering.enabled=true
  - 参考 `docs/methodologies/agent-capability-engineering.md` §8(Agent 运维)。检查技术设计(tech-design.md)是否含 `## Agent 实现` 段落,检查是否存在 Agent 评估报告(agent-eval-report.md)。
  - 条件:存在 Agent 实现规格或 agent-eval-report.md
   - 交付包追加「Agent 能力产物」段:引用方案(solution.md)的 `## Agent 架构` 和技术设计的 `## Agent 实现`、引用 Agent 评估报告路径和整体结论、列各 Agent 组件行为分布通过状态、列制度层约束执行方式(策略 / 钩子路径),说明可观测性接入方式;遗留项包含 Agent 能力已知限制。
</step>

</steps>

<failure_paths>

| 失败类型 | 触发条件 | 处理方式 |
|---|---|---|
| `verify-evidence-missing` | 验证命令证据或结果证据缺失 | 回验证阶段补证据;交付不自行降级。 |
| `user-continue-fix-implementation-bug` | 用户在第 7 步选择继续修复,且问题属于实现缺陷 | 按缺陷修复协议进入执行、代码审查和验证。 |
| `scope-adjust` | 用户要求调整范围 | 路由到过程纠偏(course-correction)。 |
| `writing-issue` | 交付文档表达问题 | 路由到接收审查反馈。 |
| `blocking-followup-not-accepted` | 阻断性后续项未被用户接受 | 发起决策门,候选处理为创建后续工作、降级为建议项或停止任务。 |
| `agent-capability-high-fail` | Agent 能力出现高严重级别失败 | 返回执行或验证阶段修复,或由用户接受风险。 |
| `gate-fail` | `harness gate transition --stage delivery` 返回失败 | 交付内修复后重跑阶段门。 |
| `handoff-pause-missing` | 移交暂停证据缺失 | 停在交付阶段,补 `harness delivery handoff --pause`。 |

</failure_paths>

阶段转换:

- 决定来源:任务切片(Mission Slice)的 `control_plane.stage`。
- 典型下一步:
  - `finishing-branch`:交付已暂停,用户或看板明确触发分支收尾。
- 执行方式:命令行接口 `harness gate advance`。

</workflow>
