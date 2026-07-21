---
name: prd
description: '当任务契约已确认、探索完成（或跳过）、需要把业务诉求产品化为产品定义包时使用。当用户说"写需求""PRD""产品定义""把需求整理一下"时也触发。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# PRD — 产品定义包

## 概述

将任务契约和探索结论转化为产品定义包。`prd` 是历史 stage key，不代表产物文件名。

产品定义包包含：

- `product/product-definition.md`：主产品定义，包含问题诊断、业务对象、系统用例、系统责任、质量与运行约束、验收场景、范围取舍、验证闭环和追溯矩阵。
- `product/product-evidence.md`：Knowledge / Spec / Graphify evidence 与降级记录。
- `product/product-domain-model.md`：按 DDD 组织的产品领域模型，包含战略 DDD（业务域、子域、限界上下文、上下文关系、统一语言、能力边界）和战术 DDD（Actor、聚合、聚合根、实体、值对象、命令、事件、不变量、策略、领域服务、状态机、权限、异常/补偿/幂等）；简单任务也必须说明不适用项及原因。

PRD 阶段不是单个全能专家写一份文档。业务对象分析、验收场景设计和范围策略由专业子专家先产出，再由 `senior-product-expert` 综合成最终产品定义包。

## 何时使用

- 当前 Mission Slice 的 lane action 指向 `prd`
- 探索证据已满足当前 action 输入要求，或治理级别允许跳过并已记录理由
- 用户说"写需求"、"整理需求"、"PRD"、"产品定义"

## 何时不使用

- 任务契约还未确认（→ 先完成任务接入）
- 已有完整产品定义包且不需要修改

## 快速参考

| 步骤 | 产出 |
|------|------|
| 读取任务契约 + 探索结论 | 输入上下文 |
| Evidence gathering | Knowledge / Spec / Graphify evidence 与降级记录 |
| 业务对象分析 | `product/business-object-analysis.md` |
| 验收场景设计 | `product/acceptance-scenarios.md` |
| 范围策略 | `product/scope-strategy.md` |
| 产品诊断 | 问题定义 + 业务价值 + 用户场景 |
| 领域建模 | DDD 战略建模 + 战术建模 + 规则约束 + 追溯 |
| 范围策略 | In/Out + 取舍 + 阶段化验证路径 |
| 综合定义 | 产品定义 + 系统责任 / 质量与运行约束 / 业务规则 / 验收场景 + 验证闭环 |
| 有效性审查 | 产品定义包 PASS / HOLD |

## 集成

| 技能 | 关系 |
|-------|------|
| `intake` | 输入：任务契约 |
| `discovery` | 输入：技术方案选择 |
| `design` | 输出：产品定义包传递给 solution / interaction / technical_analysis |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#prd--product-definition`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Business Object | Interaction / Solution / Tech Design / Verify | 下游无法判断状态、规则和验收对象 |
| Business Rule | 验收场景 / 条件 / Tests | 验收条件变成泛泛描述 |
| 验收场景 / 条件 | Interaction / Breakdown / Verify | 验收不可执行 |
| Scope Decision | Solution / Breakdown / Delivery | 未授权范围进入实现 |
| Validation Signal | Verify / Code Review | 测试通过但需求无法验收 |

按 `workflow.md` 执行详细步骤。
# 产品定义工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §2（BDD/Given-When-Then；User Story Mapping；领域建模；规格驱动开发；IEEE 29148）。
> `prd` 是历史阶段键（stage key），不再代表产物文件名；本阶段主产物是 `product/product-definition.md`。

下文出现的所有 `harness ...` 命令一律通过 harness-cli 技能调用（默认带 `--json`、读取结构化载荷、不直接拼 Bash 底层脚本，详见 `.harness/common/skills/harness-cli/SKILL.md`）。

<workflow stage="prd" version="3">

<goal>
  从任务契约出发，产出产品定义包：主产品定义、证据记录、DDD 产品领域模型、RUP 用例模型、外部行为契约和审查结论。目标是让方案、交互、技术分析、拆解和验证阶段不再猜测业务问题、系统边界、功能范围、系统行为描述、界面承载要求、规则、验收口径，以及哪些产品约束会影响实现路线。
</goal>

<role>
  你是产品定义编排者。你不把 PRD 当成单一文档目标，也不把所有产品能力塞进一个全能专家。默认先调度业务领域建模、用例建模、验收场景设计和范围策略子专家产出专业分析，再由 senior-product-expert 综合成产品定义包，最后调度只读审查员审查。文档是结果，产品判断和需求模型是核心。
</role>

<invariants>

| ID | 检查项 | 强制方式 |
|---|---|---|
| `product-definition-package` | prd 阶段必须产出 product/product-definition.md、product/product-evidence.md、product/product-domain-model.md 和 contracts/prd.contract.yaml |  |
| `prd-contract-not-fenced` | product-definition.md / product-evidence.md / product-domain-model.md 不得内嵌围栏代码块形式的 YAML 契约 / behaviour_contract / execution_result / role_verdicts | hook=harness-lint |
| `api-contract-draft-required-for-frontend-engineering` | 当 `prototype.delivery_mode=frontend_engineering` 且 mission 涉及 UI 时，必须产出 `api-contract-draft.md` | 第 5a 步 |
| `prd-contract-via-cli` | prd.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract fill/patch/record-review；`add-verdict` 仅用于导入既有 verdict manifest | hook=prd-check-contract-via-cli |
| `reviewer-readonly` | product-definition-reviewer 必须在 readonly subagent 中调用 | registry=subagents/product-definition-reviewer[readonly=true] |
| `mission-boundary` | 产品定义不得补造任务契约未授权目标；发现目标、范围、成功定义缺口时返回 NEEDS_DECISION 并回任务契约 / 用户决策 |  |
| `product-not-technical-architecture` | product-domain-model 是产品领域模型，不得决定数据库、接口、框架、存储或部署方案 |  |
| `rup-use-case-model` | PRD 必须建立业务用例、系统边界、已确认系统用例和界面承载要求；不得把业务动作直接当作系统功能 | reviewer=product-definition-reviewer |
| `system-use-case-behavior` | PRD 必须把已确认系统用例流展开为 `SUC-xx-FLOW-xx` 流步骤和 `SUC-xx-OP-xx` 系统操作，作为交互、方案、技术分析、拆解和验证阶段共同输入；后续阶段只能校验、承载和细化，不得重新定义系统行为 | reviewer=product-definition-reviewer |
| `ddd-domain-model` | product-domain-model 必须按 DDD 覆盖战略建模、战术建模、规则约束、追溯和下游消费指引；不适用项必须说明原因 | cli=harness prd domain-model-lint |
| `measurable-product-obligations` | 所有系统责任、质量与运行约束、业务规则和验收场景必须有可观察或可量化判断；禁止模糊形容词、实现泄漏 | cli=harness prd anti-pattern-scan |
| `solution-ready-product-inputs` | 产品定义包必须明确哪些用例、验收场景 / 条件、质量与运行约束、领域边界、范围取舍、依赖和风险会影响方案阶段路线选择；不得让 solution 自行从分散段落里猜 | reviewer=product-definition-reviewer |

</invariants>

<entry>
  - mission-contract 已完成 intake / discovery（或 discovery 被跳过）
  - 任务契约至少包含真实任务目标、产品故事上下文、成功定义、范围边界、约束和验证口径
  - skill-router 已判定本消息属 prd 阶段
</entry>

<exit>
  - `package-written`: 产品定义包 markdown 产物写入 prd stage worktree
  - `contract-filled`: prd.contract.yaml 已填充且 harness contract check PASS
  - `reviewer-pass`: product-definition-reviewer 在等同严格度下 PASS；或卡死后用户在 Decision Gate 上显式拥有残留风险的 approval 已记录（审查循环本身永不因轮次自动放行）
  - `gate-pass`: harness gate transition --stage prd 返回 status=pass
  - `spec-sync`: spec.enabled=true 时差量规格已产出且 delta-lint PASS
</exit>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `business-domain-modeler` | spawn | harness-runtime/harness/artifacts/${mission-id}/product/business-object-analysis.md | `.harness/common/agents/business-domain-modeler.md` |
| `use-case-modeler` | spawn | harness-runtime/harness/artifacts/${mission-id}/product/use-case-model.md | `.harness/common/agents/use-case-modeler.md` |
| `acceptance-scenario-designer` | spawn | harness-runtime/harness/artifacts/${mission-id}/product/acceptance-scenarios.md | `.harness/common/agents/acceptance-scenario-designer.md` |
| `product-scope-strategist` | spawn | harness-runtime/harness/artifacts/${mission-id}/product/scope-strategy.md | `.harness/common/agents/product-scope-strategist.md` |
| `senior-product-expert` | spawn | harness-runtime/harness/artifacts/${mission-id}/product/product-definition.md, harness-runtime/harness/artifacts/${mission-id}/product/product-evidence.md, harness-runtime/harness/artifacts/${mission-id}/product/product-domain-model.md, harness-runtime/harness/artifacts/${mission-id}/product/specs/**/spec.md | `.harness/common/agents/senior-product-expert.md` |
| `product-definition-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/product-definition-reviewer.md` |

</subagents>

<inputs>

| 引用 | 是否必需 | 平面 |
|---|---|---|
| `mission-contract.md` | true | 意图（Intent） |
| `project-context.md` | 条件必需：既有项目（brownfield） | 上下文（Context） |
| `discovery-brief.md` | 条件必需：discovery 已完成 | 上下文（Context） |
| `project-knowledge/_index.md` | 条件必需：长期知识存在 | 记忆（Memory） |
| `project-knowledge/specs/_index.md` | 条件必需：spec.enabled=true | 记忆（Memory） |
| `graphify evidence` | 条件必需：既有项目或涉及现有代码 / 架构 / 影响面 | 上下文（Context） |
| `harness.yaml` | true，通过 harness config snapshot 获取 | 记忆（Memory） |

</inputs>

<outputs>

| 产物 | 路径 | 类型 | 平面 / 校验器 |
|---|---|---|---|
| `product-definition` | `harness-runtime/harness/artifacts/${mission-id}/product/product-definition.md` | markdown | 记忆（Memory） |
| `product-evidence` | `harness-runtime/harness/artifacts/${mission-id}/product/product-evidence.md` | markdown | 证据（Evidence） |
| `product-domain-model` | `harness-runtime/harness/artifacts/${mission-id}/product/product-domain-model.md` | markdown | 记忆（Memory） |
| `business-object-analysis` | `harness-runtime/harness/artifacts/${mission-id}/product/business-object-analysis.md` | markdown | 证据 / 记忆 |
| `use-case-model` | `harness-runtime/harness/artifacts/${mission-id}/product/use-case-model.md` | markdown | 证据 / 记忆 |
| `acceptance-scenarios` | `harness-runtime/harness/artifacts/${mission-id}/product/acceptance-scenarios.md` | markdown | 证据 |
| `scope-strategy` | `harness-runtime/harness/artifacts/${mission-id}/product/scope-strategy.md` | markdown | 证据 |
| `prd-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/prd.contract.yaml` | contract | 产物契约（Artifact Contract）；校验器：`harness contract check` |

</outputs>

<method_conventions>

| 产物 | 直接使用模板的人 | 下游消费者 | 必用方法 | 模板 / 结构约定 |
|---|---|---|---|---|
| `product/business-object-analysis.md` | `business-domain-modeler` | `use-case-modeler`、`acceptance-scenario-designer`、`senior-product-expert`、`product-definition-reviewer` | 从业务名词、状态、引用关系、版本 / 停用规则和业务规则中识别业务对象，并把状态机作为与业务对象同等级的产品语义模型；排除 UI 控件、技术对象和临时动作词 | 必须使用 `harness-runtime/templates/business-object-analysis.md`；写输入合格性判断、候选对象清单、对象详情、属性、引用关系、状态机、业务规则、建模取舍和下游消费提示 |
| `product/use-case-model.md` | `use-case-modeler` | `acceptance-scenario-designer`、`product-scope-strategist`、`senior-product-expert`、交互 / 方案 / 技术分析阶段 | 按 RUP 顺序执行：输入合格性判断 → 参与者-目标矩阵 → 业务用例 → 责任切分矩阵 → 系统用例 → 系统行为描述 → 界面承载要求 → 验收推导提示 → 领域模型反馈 → 追溯矩阵 | 必须使用 `harness-runtime/templates/use-case-model.md`；编号固定为 `BUC-xx` / `SUC-xx` / `SUC-xx-FLOW-xx` / `SUC-xx-OP-xx` / `UIC-xx` / `DEC-xx`；系统用例必须引用已确认目标系统责任；系统行为描述必须追溯系统用例流、对象 / 状态机 / 规则和可观察结果；用例展开中新发现的对象 / 状态 / 规则必须写入领域模型反馈，不得静默改写业务对象或状态机；验收只作为下游场景推导提示 |
| `product/acceptance-scenarios.md` | `acceptance-scenario-designer` | `product-scope-strategist`、`senior-product-expert`、技术分析 / 拆解 / 验证阶段 | 从已确认系统用例流、业务规则和对象状态变化推导 Given-When-Then；正向、负向、边界、权限和状态限制按风险覆盖 | 必须使用 `harness-runtime/templates/acceptance-scenarios.md`；不得从待澄清系统责任派生验收条件；每条验收条件必须有可观察结果和建议证据类型；场景 / 条件 ID 作为下游追溯锚点 |
| `product/scope-strategy.md` | `product-scope-strategist` | `senior-product-expert`、交互 / 方案 / 技术分析 / 拆解阶段 | 围绕业务用例闭环、系统用例闭环、界面承载要求和验收闭环判断范围内 / 范围外 / 延后 / 待决策 | 必须使用 `harness-runtime/templates/scope-strategy.md`；范围取舍必须说明业务价值、风险、证据、任务契约追溯和对方案路线的影响 |
| `product/product-definition.md` | `senior-product-expert` | `product-definition-reviewer`、交互 / 方案 / 技术分析 / 拆解 / 验证阶段 | 综合业务对象、用例模型、验收场景和范围策略，形成可验收、可追溯的产品定义包 | 必须保留系统边界、业务用例、系统用例、系统行为描述、界面承载要求、验收场景 / 条件、质量与运行约束、方案阶段输入和追溯矩阵；不得退化为旧式功能 / 质量编号清单 |

</method_conventions>

<steps>

<step id="step-0" n="0" goal="阶段初始化">
 - 调用 `harness mission stage start --mission <mission-id> --stage prd`；stage 必须来自任务切片（Mission Slice）`control_plane.stage`，不使用额外 stage。
 - 调用 `harness trace log-init --mission <mission-id> --stage prd --json` 初始化 trace。
 - 调用 `harness context check --json`；PASS 则读取 `project-context.md`；FAIL 时按 `project-context` 规则处理，并在 evidence 中记录 `inputs_missing.project_context=true`，不得静默继续。
 - 调用 `harness config snapshot --json`，记录 `spec.enabled` 和 `agent_engineering.enabled`；不得直接读取 `harness-runtime/config/harness.yaml`。
 - 若项目存在长期知识，先读取 `project-knowledge/_index.md` 或调用 `harness knowledge resolve --stage prd --json` 获取本阶段相关知识，不得全量读取知识库。
 - 若 `spec.enabled=true`，读取 `project-knowledge/specs/_index.md` 并解析当前能力基线；产品定义必须标注新增/修改/移除的能力与既有 spec 的关系。
 - 若是既有项目，或任务 / 探索涉及现有代码、架构、调用链、模块边界、影响面，叠加 `graphify-exploring` / `graphify-impact-analysis` 作为证据来源；不可用时在 `product-evidence.md` 与 contract degradations 中记录降级原因和补救动作。
 - 使用 `harness frame current --mission <mission-id> --json` 返回的任务切片（Mission Slice）快照；消费 `work_graph.primary_nodes`、stage `output_artifact`、`graph_operation` 和 role policy。
 - 若任务契约缺真实任务目标、用户 / 问题 / 场景 / 价值 / 成功指标、成功定义、范围边界或验证口径，停止并回任务契约决策；不得让产品专家补造。
</step>

<step id="step-1" n="1" goal="专业子专家按依赖图产出产品定义输入">
 PRD 子专家不是固定全串行，也不是无条件并行。并行只允许发生在同一 barrier 内，且每个子专家 Task Envelope 声明的输入产物必须已经存在；读取尚未完成的路径视为流程错误。

 依赖图：

 | Barrier | 可并行动作 | 必须等到 | 产物 |
 |---|---|---|---|
 | A | 业务材料 / 知识 / 证据摘要可并行准备 | 任务契约、探索简报和项目知识输入就绪 | 输入摘要 |
 | B | `business-domain-modeler` | Barrier A 完成 | `business-object-analysis.md`，含业务对象和状态机基线 |
 | C | `use-case-modeler`；如任务包含多个相互独立业务用例，可在 role 内按 `BUC-xx` 分片并行，但共享状态机 / 业务规则变更必须同步 | Barrier B 完成 | `use-case-model.md`，含系统行为描述和领域模型反馈 |
 | D | `acceptance-scenario-designer` 可先按系统用例流生成验收场景；`product-scope-strategist` 可先做范围草案，但最终范围结论必须等待验收场景完成 | Barrier C 完成；scope 最终版还必须等待 acceptance 完成 | `acceptance-scenarios.md`、`scope-strategy.md` |
 | E | `senior-product-expert` 综合 | Barrier D 全部完成且无 BLOCKED / NEEDS_DECISION | 产品定义包 |

 通过 `@business-domain-modeler` native delegation调用 `business-domain-modeler` subagent（Cursor auto-routes 到对应 agent registry 项）
 - Task Envelope：任务契约、discovery-brief（如有）、知识解析摘要、project-context、业务参考材料、模板 `harness-runtime/templates/business-object-analysis.md`、输出路径 `product/business-object-analysis.md`、write_scope、完成条件。
 - 产物要求：必须给出业务对象基线和状态机基线；状态机至少包含归属对象 / 聚合、状态集合、触发事件 / 命令、合法迁移、非法迁移、前置条件 / 守卫和关联规则 / 用例线索。
 - BLOCKED 路由：返回 NEEDS_DECISION / BLOCKED 时记录原因，向用户发起决策门；不得让 senior-product-expert 猜测业务对象后继续。
 - Barrier B：只有 `business-object-analysis.md` 完成且没有阻断时，才能启动 `use-case-modeler`。

 通过 `@use-case-modeler` native delegation调用 `use-case-modeler` subagent（Cursor auto-routes 到对应 agent registry 项）
 - Task Envelope：任务契约、discovery-brief（如有）、business-object-analysis 路径、知识 / 规格 / project-context 摘要、模板 `harness-runtime/templates/use-case-model.md`、输出路径 `product/use-case-model.md`、write_scope、完成条件。
 - 产物要求：系统用例必须引用已确认目标系统责任；必须把系统用例流展开成 `## 系统行为描述`，每个关键步骤使用 `SUC-xx-FLOW-xx`，每条系统操作使用 `SUC-xx-OP-xx`，并至少说明触发、目标系统操作、对象 / 状态迁移 / 规则和可观察结果；每个会改变业务对象、状态机或业务规则的用例发现，必须写入 `## 领域模型反馈`，交给 senior-product-expert 统一裁剪和回写产品领域模型。
 - BLOCKED 路由：返回 NEEDS_DECISION / BLOCKED 时记录原因，向用户发起决策门；不得让 acceptance-scenario-designer 或 senior-product-expert 补造系统责任后继续。
 - Barrier C：只有 `use-case-model.md` 完成且领域模型反馈已显式标注处理方式时，才能启动验收场景最终生成和范围最终判断。

 通过 `@acceptance-scenario-designer` native delegation调用 `acceptance-scenario-designer` subagent（Cursor auto-routes 到对应 agent registry 项）
 - Task Envelope：任务契约、discovery-brief（如有）、business-object-analysis 路径、use-case-model 路径、风险 / 依赖摘要、模板 `harness-runtime/templates/acceptance-scenarios.md`、输出路径 `product/acceptance-scenarios.md`、write_scope、完成条件。
 - BLOCKED 路由：返回 NEEDS_DECISION / BLOCKED 时记录原因，向用户发起决策门；不得让 senior-product-expert 补造可观察验收口径。

 通过 `@product-scope-strategist` native delegation调用 `product-scope-strategist` subagent（Cursor auto-routes 到对应 agent registry 项）
 - Task Envelope：任务契约、discovery-brief（如有）、business-object-analysis 路径、use-case-model 路径、acceptance-scenarios 路径、知识 / 规格 / Graphify 证据摘要、模板 `harness-runtime/templates/scope-strategy.md`、输出路径 `product/scope-strategy.md`、write_scope、完成条件。
 - BLOCKED 路由：返回 NEEDS_DECISION / BLOCKED 时记录原因，向用户发起决策门；不得继续综合。
 - Barrier D：`acceptance-scenarios.md` 和 `scope-strategy.md` 都完成后，才能进入 senior-product-expert 综合；不得让 senior-product-expert 在缺少验收或范围结论时自行补齐。
</step>

<step id="step-2" n="2" goal="资深产品专家综合产品定义包">
 通过 `@senior-product-expert` native delegation调用 `senior-product-expert` subagent（Cursor auto-routes 到对应 agent registry 项）
 - 任务信封包含：任务契约、project-context、discovery-brief（如有）、知识解析摘要、规格基线摘要、Graphify 证据（如有）、`business-object-analysis.md`、`use-case-model.md`、`acceptance-scenarios.md`、`scope-strategy.md`、专业子产物模板、模板 `product-definition.md` / `product-evidence.md` / `product-domain-model.md`、输出路径、write_scope、完成条件。
 - senior-product-expert 必须按内部流程完成：任务就绪判断 → 证据收集 → 问题诊断 → 专业产物综合 → 产品领域模型 → 用例模型综合 → 系统行为描述发布 → 界面承载要求 → 范围 / 取舍 → 方案阶段输入收束 → 产品定义 → 产品定义包完整性检查。
 - 必须写入 `product/product-definition.md`、`product/product-evidence.md` 和 `product/product-domain-model.md`。领域模型是产品阶段核心产物；必须消费业务对象分析中的核心对象、状态机、引用关系和规则，并消解用例模型中的领域模型反馈；不适用的 DDD 要素必须说明原因，但不得为了填空引入虚假聚合或技术实现概念。
 - `product/product-definition.md` 必须明确业务用例、系统边界、已确认系统用例、系统行为描述、界面承载要求、验收场景 / 条件和质量与运行约束之间的关系；原型阶段应能据此判断需要设计哪些用户任务、信息展示、输入、状态、错误、权限和反馈。
 - `product/product-definition.md` 必须写出 `## 方案阶段输入`：把会影响实现路线的系统行为描述、核心系统用例、关键验收场景 / 条件、质量与运行约束、领域边界、范围取舍、依赖、风险、界面承载要求和 Agent 能力要求集中说明。这里只说明产品语义和约束，不选择技术路线。
 - `product/product-evidence.md` 必须写出 `## 影响方案路线的事实与风险` 和 `## 不得带入方案阶段的假设`；证据不足且会影响路线选择时，必须返回 NEEDS_DECISION / BLOCKED 或回流探索，不得让 solution 以假设继续。
 - `product/product-domain-model.md` 必须写出 `## 给方案阶段的领域边界`：明确方案阶段必须保留的限界上下文、聚合一致性边界、策略、领域事件、不变量、状态机和权限语义，以及破坏这些语义的风险。
 - 会改变方案路线的问题不得只留在“待澄清问题”里放行。若缺口会改变用户可观察行为、系统边界、质量与运行约束、领域规则、范围取舍或风险处理方式，必须在 PRD 阶段阻断、回流或发起用户决策。
 - `product/product-definition.md` 是主产品定义正文。Markdown 只能引用外部 `contracts/prd.contract.yaml`，不得内嵌 contract YAML。
 - 主流程从 senior-product-expert 返回摘要中提取 behaviour contract 字段，通过 `harness contract init` / `harness contract patch` 写入 contract。
 - 条件：senior-product-expert 返回 NEEDS_DECISION / BLOCKED
  - 调用 `harness contract add-execution-result` 或 `harness contract patch` 记录阻塞原因，向用户发起决策门；不得继续审查或下游推进。
</step>

<step id="step-3" n="3" goal="反模式自检">
 - 调用 cli `harness prd anti-pattern-scan` `--artifact harness-runtime/harness/artifacts/${mission-id}/product/product-definition.md`，evidence=required。
 - 调用 cli `harness prd domain-model-lint` `--artifact harness-runtime/harness/artifacts/${mission-id}/product/product-domain-model.md --product-definition harness-runtime/harness/artifacts/${mission-id}/product/product-definition.md`，evidence=required。
 - 条件：findings 非空
  - 按 typed `{rule, location, evidence}` 逐条修复 product-definition.md / product-evidence.md / product-domain-model.md
  - 重新调用 `harness prd anti-pattern-scan` 和 `harness prd domain-model-lint`，直到 `status=PASS`
</step>

<step id="step-4" n="4" goal="契约初始化与状态更新">
 - 调用 cli `harness contract init` `--mission ${mission-id} --stage prd --template prd`，evidence=required。
 - 通过 `harness contract patch` 写入 `product_definition_package`、`domain_model`（含 `state_machines`）、`covers_intent`、`user_story_mapping`、`behavior_specs`、`non_behavior_specs`、`business_rules`、`product_metrics`、`risks`、`dependencies`、`execution_result`。
 - 调用 cli `harness prd domain-model-lint` `--artifact harness-runtime/harness/artifacts/${mission-id}/product/product-domain-model.md --product-definition harness-runtime/harness/artifacts/${mission-id}/product/product-definition.md --contract harness-runtime/harness/stages/${mission-id}/contracts/prd.contract.yaml`，evidence=required。
 - 调用 `harness contract check --artifact contracts/prd.contract.yaml --upstream mission-contract.contract.yaml --json`；FAIL 必须修复后再继续。
</step>

<step id="step-5" n="5" goal="工作图产物绑定">
 - 确认本阶段 stage 来自 `work_graph.lanes`，不得另造映射。
 - 绑定任务切片（Mission Slice）primary node + artifact store output_artifact + graph_operation + work_graph_artifact.artifact_refs。主产物为 `product-definition.md`；artifact refs 包含证据、业务对象分析、用例模型、验收场景、范围策略、领域模型和可选 specs。
 - PRD 工作流只写阶段目录和外部契约；工作图写入在阶段门 PASS 后的 `harness gate advance`。
</step>

- 条件：`prototype.delivery_mode=frontend_engineering` 且任务涉及 UI（**默认按涉及处理**，由 PRD 据 `product-definition.md` 判断；仅明确纯后端 / 接口 / 数据 / CLI 无界面时跳过。不再用 `harness interaction check-ui-trigger` 的 UIC 结论判定——该判定已移到 interaction 阶段内）
 <step id="step-5a" n="5a" goal="产出 api-contract-draft.md（前端契约草案）">
  - 模板：`harness-runtime/templates/api-contract-draft.md`。
  - 写入路径：`harness-runtime/harness/stages/${mission_id}/api-contract-draft.md`。
  - 内容：endpoint 总览（method / path / 描述 / traces_to 验收场景或验收条件 ID / 鉴权幂等限流备注）+ shared types 草图（领域实体、状态枚举、Request / Response 形状）+ 错误码 + 演示分支 scenarios + 鉴权/权限/数据边界 + 非 endpoint 形态 + open questions。
  - 这是交互阶段（prototype-as-frontend 路线）frontend-prototype-engineer 抽取 `lib/types/` 草案的输入；粒度是草案，不是完整 OpenAPI。
  - 同步在 `prd.contract.yaml` 的 `artifact_refs` 段引用此文件。
  - 不在 frontend_engineering 路线时跳过此步。
 </step>

- 条件：spec.enabled=true
 <step id="step-6" n="6" goal="产出差量规格（行为契约增量）">
  - 参考 `project-knowledge/specs/_index.md` 格式说明 + `harness-runtime/templates/delta-spec.md` 模板。
  - 从 discovery brief、用例模型的系统行为描述或 product-definition.md 的系统责任反推能力清单。
  - 对每个能力产出差量规格：定位基线 → 分类 Requirement（ADDED/MODIFIED/REMOVED）→ 写 Scenario（四级标题 `####`，GIVEN/WHEN/THEN）→ 写入 `harness-runtime/harness/artifacts/<mission-id>/product/specs/<capability>/spec.md`。
  - 调用 cli `harness spec delta-lint` `--mission ${mission-id} --capability ${capability-name}`，evidence=required。
  - 条件：delta-lint FAIL
   - 按 `findings` 修正差量规格后重新 lint
  - 同步更新 `prd.contract.yaml` capabilities[] 的 delta_spec / requirement_ids / scenario_ids / traces_to。
 </step>

- 条件：agent_engineering.enabled=true
 <step id="step-7" n="7" goal="补充 Agent 能力 Requirements">
  - 检查任务契约 `## Agent Engineering` 段落和 product-definition.md 的 Agent 能力要求。
  - 条件：存在 Agent 组件标记
   - 调用 cli `harness prd agent-cap-eval` `--mission ${mission-id} --component ${name} --work-rights ${list} --priority ${P}`，evidence=required。
   - 与 contract `agent_capability_requirements[]` 同步。
 </step>

<step id="step-8" n="8" goal="产物阶段门自检">
 - 调用 cli `harness gate transition` `--stage prd --mission ${mission-id} --artifact harness-runtime/harness/artifacts/${mission-id}/product/product-definition.md --contract-artifact harness-runtime/harness/stages/${mission-id}/contracts/prd.contract.yaml --mission-slice ${path}`，evidence=required。
 - 条件：gate status=FAIL
  - 按 `failed_step` / `failed_checks` 逐条修复产品定义包或 contract，重新 `gate transition` 直到 PASS。
</step>

<step id="step-9" n="9" goal="产品定义有效性审查（审查-修复循环）">
 - 循环：id=reviewer-loop；无轮次放行（producer-fixable 缺口不设通过上限，轮次只记录修复历史）；退出条件：product-definition-reviewer 在等同严格度下返回 PASS / 无阻断
  - 每轮审查返回后调用 `harness contract record-review --artifact harness-runtime/harness/stages/${mission-id}/contracts/prd.contract.yaml --role product-definition-reviewer --verdict <PASS|PASS_WITH_RISK|HOLD|BLOCKED> --subagent-id <dispatch-id> --model <resolved-model> --review-basis harness-runtime/harness/stages/${mission-id}/product/product-definition.md --summary <review-summary> --json`，由 CLI 维护 `role_verdicts` 与 `effectiveness_review.rounds_used`。
  通过 `@product-definition-reviewer` native delegation调用 `product-definition-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
  - 任务信封：product-definition.md、product-evidence.md、product-domain-model.md、business-object-analysis.md、use-case-model.md、acceptance-scenarios.md、scope-strategy.md、contract 路径、任务契约、探索简报、project-context、差量规格路径、只读约束、产品定义审查清单、方案阶段输入检查清单、审查结论格式。

  - 分支：审查结论
   - 情况：HOLD / BLOCKED
    - 修复产品定义包阻断性问题，记录发现和修复内容。
    - 用 `harness contract record-review` 记录 HOLD / BLOCKED verdict 与 `--blocking-gap`；如需设置 `pending_reviewer_recheck=true`，通过 `harness contract patch --artifact harness-runtime/harness/stages/${mission-id}/contracts/prd.contract.yaml --patch <pending-recheck-patch.yaml> --json` 写入，不手工编辑 contract。
    - 立即重新 dispatch product-definition-reviewer 全量审查。
    - Hard gate `no-skip-recheck`：
     - 修复完成不等于审查通过。只有 reviewer 确认无阻断且 pending_reviewer_recheck=false 才能退出。
     - 强制方式：hook=prd-check-pending-recheck
   - 情况：PASS
    - 审查通过，退出循环。

 - 条件：卡死——同一阻断在修复后，product-definition-reviewer 仍以相同根因连续 HOLD 且无实质进展（按缺口本质判断，不是"轮次到点"）
  - 不得降级通过。按 `core.md`「严格审查不变量」重新归因：producer 能补但反复没补对 → 留在循环升级修复策略 / reviewer 模型继续重做；本质是真实信息缺失或任务契约范围本身需调整 → 回 intake。
  - 仅当确需用户在范围 / 路线上拍板才能解时，调用 tool: `AskUserQuestion`。
   - 问题：产品定义审查以下阻断在反复修复后仍无法在当前范围内解决（已附完整未解决阻断清单与卡点根因），最近 verdict 为 ${last_verdict}，需要你决策方向：
   - 候选答案（**不含"接受当前产品定义包 / 降级通过"**）：
      - 给出修复方向，留在审查循环继续重做
      - 调整任务契约范围（回 intake）
      - 升级 BLOCKED，终止本阶段
  - 残留风险只能由用户在充分披露完整未解决阻断后于 Decision Gate 显式拥有：仅此时调用 cli `harness approval append` `--mission ${mission-id} --type tradeoff --stage prd --status approved`，evidence=required；审查循环本身永不把未解决阻断自动转为通过。

 - 审查摘要附加到 product/product-definition.md 末尾；结构化审查结论通过 `harness contract record-review --artifact harness-runtime/harness/stages/${mission-id}/contracts/prd.contract.yaml --role product-definition-reviewer --verdict <PASS|PASS_WITH_RISK|HOLD|BLOCKED> --subagent-id <dispatch-id> --model <resolved-model> --review-basis harness-runtime/harness/stages/${mission-id}/product/product-definition.md --summary <review-summary> --json` 写入 contract。只有导入既有 verdict manifest 时才使用 `harness contract add-verdict`。
</step>

<step id="step-10" n="10" goal="阶段退出">
 - 确认第 8 步 `gate transition` PASS 且第 9 步审查员 PASS / approval；阶段完成、Gate 报告、Work Graph operation、下一 Mission Slice 由 `gate transition` 写入，不再单独调用 `mission stage complete` / `gate advance` / `board select`。
</step>

</steps>

<failure_paths>

| 失败 | 触发 | 处理 |
|---|---|---|
| `product-specialist-blocked` | business-domain-modeler / acceptance-scenario-designer / product-scope-strategist 返回 BLOCKED / NEEDS_DECISION | 记录业务对象、验收口径或范围策略缺口，向用户发起决策门；不得由 senior-product-expert 猜测后继续。 |
| `use-case-modeler-blocked` | use-case-modeler 返回 BLOCKED / NEEDS_DECISION | 记录系统边界、系统责任、用例流或界面承载义务缺口，向用户发起决策门；不得由后续专家把未确认责任写成系统用例或验收条件。 |
| `senior-product-expert-blocked` | senior-product-expert 返回 BLOCKED / NEEDS_DECISION | 记录真实问题、业务目标、成功定义、领域规则、范围取舍、方案阶段输入、风险接受或任务契约匹配缺口，向用户发起决策门；不得默认收缩范围。 |
| `reviewer-blocked` | product-definition-reviewer 返回 BLOCKED / HOLD | 按第 9 步审查-修复循环处理；卡死（修复后仍以相同根因连续 HOLD 无进展）时重新归因，需用户拍板则 AskUserQuestion（候选仅：继续修 / 回 intake / 升级 BLOCKED，不含降级通过）。 |
| `contract-check-fail` | harness contract check FAIL | 按 findings 逐条修复 contract 字段；不得用 --allow-placeholders 跳过。 |
| `gate-transition-fail` | harness gate transition FAIL | 按 failed_step / failed_checks 逐条修复，重新 gate transition。 |

</failure_paths>

阶段流转：

- 决定来源：任务切片（工作图）中的 `control_plane.stage`。
- 常见下一阶段：
  - `interaction`：UI / 用户旅程 / 状态交互 / 原型需要独立设计；发生在产品定义之后、方案阶段之前
  - `solution`：需要方案路线选择 / 取舍 / 架构级产品到技术路线映射
  - `technical_analysis`：需要技术设计
  - `breakdown`：低复杂度且已具备足够产品定义和实现边界
- 强制方式：cli=harness gate advance

</workflow>
