# 探索工作流

> **触发条件（何时使用 / 跳过 / 硬关口（HARD-GATE））和行为约束（反合理化）见 `SKILL.md`，不在此重复。**
> **方法论参考**：`.harness/docs/methodology-reference.md` §1（事件风暴（Event Storming）— Brandolini；影响地图（Impact Mapping）— Adzic；待完成工作（Jobs-to-be-Done）— Christensen）

下文出现的所有 `harness ...` 命令一律通过 harness-cli 技能调用（默认带 `--json`、消费类型化载荷（typed payload）、不直接拼 Bash 底层脚本，详见 `.harness/common/skills/harness-cli/SKILL.md`）。

<workflow stage="discovery" version="2">

<goal>
  对问题空间做深度探索，识别隐藏约束、技术风险、信息空白，以及产品定义阶段（PRD）建立统一过程（RUP）用例模型所需的业务场景、系统边界和责任划分线索，产出结构化探索简报（discovery-brief）给下游产品定义 / 设计阶段使用。
</goal>

<role>
  你先是问题空间侦察者，再是简报作者。先做事实采集（Graphify 索引 / 规格影响面 / 现有方案 / 用户角色 / 业务活动 / 系统边界 / 智能体化（Agent 化）候选），把每条结论标注证据或推断链，再写人读叙事。不替产品定义阶段（PRD）产出业务对象模型、系统用例、验收条件或原型方案；只发现事实、线索和需要产品定义阶段决策的问题。
</role>

<invariants>

| ID | 检查项 | 强制方式 |
|---|---|---|
| `discovery-brief-not-fenced` | `discovery-brief.md` 不得内嵌围栏 YAML（fenced YAML）控制契约段 | cli=harness contract check |
| `discovery-contract-via-cli` | `discovery-brief.contract.yaml` 由 `harness contract fill` / `patch` 写入，智能体（agent）不直接 Edit/Write | hook=discovery-check-stage-worktree |
| `reviewer-readonly` | discovery-effectiveness-reviewer 必须在只读子智能体（readonly subagent）中调用（`strict_mode` 白名单） | registry=subagents/discovery-effectiveness-reviewer[readonly=true,strict_mode=true] |
| `brownfield-graphify-evidence` | 既有项目任务下 `existing_solutions[].source` 至少一条 `graphify_*`，或 `degradations[]` 显式确认（acknowledge） | hook=discovery-check-graphify-brownfield<br>cli=harness contract check |
| `spec-coverage` | `spec.enabled=true` 时 `affected_capabilities` 必须覆盖 `project-knowledge/specs/` 所有能力（capability） | cli=harness contract check |
| `agentize-four-of-four` | `recommended=agentize` 必须 4 个布尔值（boolean）全为 true | cli=harness discovery agent-eng-eval |
| `rup-prd-handoff` | 探索阶段（discovery）必须给产品定义阶段（PRD）用例建模提供业务场景、系统边界 / 责任划分和原型承载线索；不得把这些线索写成最终系统用例或页面方案 | reviewer=discovery-effectiveness-reviewer |

</invariants>

<entry>
  - mission-contract 已写入（intake stage 完成）
  - skill-router 判定本消息属探索阶段（discovery）（或 discovery 在 `skippable_stages` 中且通过 `harness discovery skip` 显式跳过）
</entry>

<exit>
  - `brief-written`: `discovery-brief.md` 写入探索阶段（discovery）的阶段工作树（worktree）
  - `contract-filled`: `discovery-brief.contract.yaml` 已填充且 `harness contract check` 通过（PASS，含 `W-spec-coverage` / `W-discovery-contract` / `W-graphify-source` 三规则）
  - `reviewer-pass`: discovery-effectiveness-reviewer 在等同严格度下通过（PASS）；或卡死后用户在 Decision Gate 上已显式裁决方向（回框定 / 改范围 / 升级 BLOCKED）并有记录——审查循环本身永不因轮次用尽自动放行
  - `user-confirmation`: `approvals.json` 含 `discovery_confirmation` 已批准（approved），或 `discovery_skip` 已记录
  - `gate-pass`: `harness gate run --stage discovery` 返回 `status=pass`
</exit>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `discovery-analyst` | spawn | harness-runtime/harness/artifacts/${mission-id}/discovery/discovery-brief.md, harness-runtime/harness/stages/${mission-id}/contracts/discovery-brief.contract.yaml | `.harness/common/agents/discovery-analyst.md` |
| `discovery-effectiveness-reviewer` | spawn readonly |  | `.harness/common/agents/discovery-effectiveness-reviewer.md` |

</subagents>

<inputs>

| 引用 | 是否必需 | 平面 |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `project-context.md` | 条件必需：既有项目（brownfield） | Context |
| `project-knowledge/specs/**` | 条件必需：`spec.enabled=true` | Memory |
| `harness.yaml` | 必需：通过 `harness config snapshot` 获取 | Memory |
| `graphify-out/` | 条件必需：既有项目，通过 `harness graphify status` 获取 | Context |

</inputs>

<outputs>

| 产物 | 路径 | 类型 | 平面 / 校验器 |
|---|---|---|---|
| `discovery-brief-md` | `harness-runtime/harness/artifacts/${mission-id}/discovery/discovery-brief.md` | markdown | Memory |
| `discovery-brief-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/discovery-brief.contract.yaml` | contract | 产物契约（Artifact Contract）；校验器：`harness contract check` |

</outputs>

<steps>

<step n="0" goal="进入探索阶段（discovery）并初始化控制面">
 - 通过 harness-cli 技能调用 `harness mission stage start --mission <id> --stage discovery --json`，写入阶段入栈记录。
 - 调 `harness trace log-init --mission <id> --stage discovery --json` 引导 trace JSONL。
 - 调 `harness context check --json`：通过（PASS）则读 `project-context.md`；失败（FAIL）时按 `project-context` 规则处理，并在探索简报证据中记录 `inputs_missing.project_context=true`，不得静默继续。
 - 调 `harness config snapshot --json` 读取 `spec.enabled`（决定第 3 步是否执行）与 `agent_engineering.enabled`（决定第 7 步是否执行）。不得直接读取 `harness-runtime/config/harness.yaml`。
 - 调 `harness graphify status --json` 写入 trace；`available=true && fresh=true` ⇒ 第 2 步可直接走 Graphify 证据；`available=false` 或 `fresh=false` ⇒ 第 2 步进入降级（degradation）路径。
 - 调 `harness frame current --mission <id> --json` 读复杂度、`autonomy_level` 和 `skippable_stages`；若探索阶段在 `skippable_stages` 中且任务为全新项目（`graphify.available=false` 且无触发关键词），可走 `harness discovery skip --mission <id> --reason <text> --json` 跳过探索。
 - 条件：探索阶段已跳过
  - 跳到第 11 步阶段退出门（stage exit gate），不进入第 1-10 步。
 - 条件：探索阶段不跳过
  - 读取探索阶段角色策略（role policy）；未配置时默认执行子智能体（Agent）为 `discovery-analyst`；继续第 1 步。
</step>

<step n="1" goal="专业角色调度">
 - 通过 `Task(subagent_type="discovery-analyst", prompt=<Task Envelope>)` 工具调用 `discovery-analyst` subagent，仅追加路径化任务信封；任务信封只包含：任务目标、输入路径（任务契约、`project-context` 如存在、`project-knowledge/specs` 索引如启用）、输出路径、`write_scope`、可用工具（Graphify 可用性只给状态和查询入口，不粘贴大段结果）和事实来源 / 置信度要求。角色提示由安装时物化的 `.<adapter>/agents/discovery-analyst.md` 加载，工作流（workflow）内不再复制原文，也不得复述或改写 discovery-analyst 的角色边界。
 - `discovery-analyst` 不负责直接写任务切片、`mission-status` 或控制面 YAML；它只写探索简报（discovery-brief）并返回完成（DONE）/ 阻断（BLOCKED）与执行结果建议摘要。主流程负责登记证据和状态。
</step>

<step n="2" goal="问题空间分析">
 - 从任务契约出发，分析：

 **当前现状**
 - 现在的流程/系统是怎样的（既有项目从代码库和 project-context 分析）
 - 谁在用、怎么用、痛点在哪

 - 条件：既有项目=true 或任务明确要求项目/代码/架构/调用链/执行流分析
 - 硬关口（HARD-GATE）：调 `harness graphify status --json` 读 `{available, indexed, fresh}`。`available=true && fresh=true` 时继续走 Graphify 证据路径；否则强制把对应 `graphify_unavailable` / `graphify_stale` 一条写入 `discovery-brief.contract.yaml.degradations[]`（缺该记录时第 9 步审查员会保持（HOLD））。
 - 使用 `graphify-exploring` 建立现有代码事实：
 - READ ``mcp__graphify__query_graph``，确认目标仓库是否已索引
 - READ ``harness graphify status` + `graphify-out/GRAPH_REPORT.md``，记录索引新鲜度和代码库概览
 - `graphify_query({query: "<本次任务相关概念>"})`，定位相关模块和执行流
 - 对关键符号执行 `graphify_context({name: "<symbol>"})`，确认调用关系
 - 将 Graphify 证据写入 `discovery-brief.contract.yaml.existing_solutions[]`（`source = graphify_symbol / graphify_query`，`reference = graphify` 路径），并在简报正文「现有方案分析」段引用。
 - 条件：Graphify 不可用 / 未索引 / 索引过期
 - 记录降级原因，不得静默回退
 - 给出补救动作，例如 `graphify .`；再用手动代码搜索作为临时证据

 **问题拆解**
 - 核心问题是什么（不是表面症状，是根因）
 - 核心问题可以拆成哪几个子问题
 - 哪些子问题是本次任务要解决的，哪些不是

 **业务对象候选**
 - 从任务契约、project-context、现有代码、文档和接口材料中识别候选业务对象：被用户持续谈论、操作、追踪、约束或承载生命周期的业务名词。
 - 业务对象候选识别方法：先抽取业务名词，再用五问过滤：业务人员是否会谈论它；是否会操作或追踪它；是否有状态、生命周期或规则；是否与其他业务对象存在关系；是否不是单纯界面（UI）控件、技术模块、接口端点、数据库表或一次性动作。
 - 业务对象候选约定模板：`候选对象 / 来源证据 / 状态-规则-关系线索 / 疑点或命名冲突 / 产品定义阶段（PRD）建模提示`。候选对象没有证据时，不写成对象，只写入疑点。
 - 只记录候选对象、别名 / 命名冲突、来源证据、状态 / 规则 / 关系线索、边界不清点和需要产品定义阶段（PRD）建模的问题；不得在探索阶段（discovery）产出最终业务对象模型、聚合、数据表或接口设计。
 - 明确排除纯界面（UI）控件、页面、按钮、技术模块、接口端点、数据库表名和一次性动作；除非它们在业务上需要被独立追踪，才可作为记录类业务对象候选。

 **系统边界与责任划分线索**
 - 从任务契约、现有系统、业务流程、外部接口和用户材料中识别：人工活动、当前系统已承担的活动、目标系统可能需要承担的活动、外部系统活动和不在本轮范围的活动。
 - 系统边界识别方法：对每个业务活动分别判断人工责任、当前系统责任、目标系统责任线索、外部系统责任和不在本轮范围的责任；目标系统责任必须写成线索或待澄清问题，不能直接升级为系统功能。
 - 每条责任划分必须标注证据等级：已确认（CONFIRMED）/ 推断（INFERRED）/ 假设（ASSUMED）。只有有明确上游表达、现有系统行为、项目文档或代码证据的内容才能标记为已确认（CONFIRMED）。
 - 责任划分约定模板：`业务活动 / 人工责任 / 当前系统责任 / 目标系统责任线索 / 外部系统责任 / 证据等级 / 待澄清点`。没有直接证据的目标系统责任必须标为推断（INFERRED）或假设（ASSUMED）。
 - 对会改变流程、权限、自动化程度、系统边界或产品范围的未确认责任，写成产品定义阶段（PRD）待澄清问题；不得在探索阶段（discovery）把它改写为系统用例。
 - 识别哪些业务场景可能需要界面（UI）承载，并记录需要展示的信息、需要输入的业务数据、需要表达的状态 / 错误 / 权限 / 反馈线索；不得决定页面数量、布局、组件或导航方案。
 - 原型承载线索模板：`场景 / 任务 / 是否可能需要界面（UI）承载 / 需要展示的信息 / 需要输入或操作 / 状态-错误-权限-反馈线索 / 证据或疑点`。只能记录承载线索，不得输出页面、组件、布局或导航方案。

 **约束识别**
 - 技术约束（从 project-context和现有代码）
 - 业务约束（从任务契约的 constraints）
 - 时间/资源约束
</step>

- 条件：spec.enabled=true
 <step n="3" goal="识别受影响能力（规格基线对照）">
 <!--
 探索的核心产出之一：回答「本次任务会碰到项目行为契约的哪些部分」。
 结论将作为产品定义阶段（PRD）第 7 步产出差量规格的能力来源。
 -->
 - 先调 `harness spec scan --mission <id> --scope-in <path1> --scope-in <path2> --json` 取候选能力（capability）列表（CLI 用能力名 vs `scope_in` 子串匹配自动给出已确认（CONFIRMED）/ 假设（ASSUMED）初判）。
 - 对每个候选能力读取其 `spec.md` 中的需求（Requirement）清单，把 CLI 初判升级为最终置信度（confidence）：

 | 判断 | 置信度 | 写入方式 |
 |------|------|---------|
 | 有规格文本直接对应任务契约的 `scope_in` | **已确认（CONFIRMED）** | 标注引用的需求（Requirement）名 + 基线规格路径 |
 | 基于架构/依赖推断会影响，但无直接规格文本证据 | **不确定（UNCERTAIN）** | 标注推断链路（为什么怀疑会影响） |
 | 完全不在规格中但任务明显涉及（新能力） | **假设（ASSUMED，新建）** | 标注「本任务将首次为 `<capability>` 建立规格」 |

 - 硬关口：不允许把置信度当摆设。每条必须有证据或推断链，不能写“可能”、“大概”。

 - 把结论写入 `discovery-brief.contract.yaml.affected_capabilities[]`（每条：`capability` / `requirement_id` / `confidence` / `evidence_or_inference`）；不在简报正文内嵌围栏 YAML（fenced YAML），简报只保留人读叙事。

 - 条件：发现已确认（CONFIRMED）或高置信不确定（UNCERTAIN）的影响面显著超出任务契约的 `scope_in`
 - 暂停探索（HALT discovery）；调用 AskUserQuestion 工具（Claude）/ question tool（OpenCode）/ equivalent，提供以下 4 项类型化候选（用户回答的枚举值写入 `harness approval append --type checkpoint --stage discovery --checkpoint discovery_scope_overflow --status approved --comment "<enum>" --json`）：
 - `expand_scope`：扩范围（回任务接入阶段（intake）重写任务契约的 `scope_in`；本次探索暂停且不写简报）
 - `shrink_solution`：缩方案（保 `scope` 不变，调整探索输出仅覆盖 `scope_in` 内）
 - `redo_intake`：重做任务接入（intake）（重写任务契约，整个任务回第 1 阶段）
 - `accept_degradation`：接受现状降级（把超 `scope` 的能力标记为假设（ASSUMED）+ 记入 `design_assumptions[].impact_on=prd`）
 - 不允许 discovery-analyst 自行选择；得到用户枚举回答后按对应路径继续或回滚。
 </step>

<step n="4" goal="用户角色与场景分析">
 - 识别所有相关的用户角色：

 | 角色 | 核心诉求 | 使用频率 | 技术水平 |
 |------|---------|---------|---------|
 | | | | |

 - 为每个角色识别关键场景：
 - 主要使用场景（顺利路径）
 - 异常场景
 - 边界场景（首次使用、极端数据、权限不足）
 - 对每个关键场景补充 discovery 级别的用例建模线索：
 - 该场景对应的业务目标和业务结果是什么。
 - 该场景中哪些活动看起来是人工完成、当前系统完成、目标系统可能完成或外部系统完成。
 - 哪些目标系统责任已经有证据，哪些会影响产品定义阶段（PRD）的系统用例建模但还不能确认。
 - 该场景是否可能需要原型 / 界面（UI）承载；如果需要，记录业务信息展示、用户输入、状态 / 错误 / 权限 / 反馈线索。
</step>

<step n="5" goal="现有方案调研">
 - 分析当前的解决方案（如果有）：
 - 现有方案为什么不够好
 - 现有方案哪些部分可以复用
 - 现有方案的用户反馈（如果可获取）

 - 条件：存在现有代码方案且 graphify-exploring 可用
 - 用 Graphify 查相关执行流和模块边界，避免只凭目录名或 grep 推断架构
 - 至少记录：相关 cluster/process、关键符号、调用关系、可复用点和风险点

 - 如果是全新领域，分析：
 - 同类产品/功能的常见做法
 - 行业最佳实践
 - 已知的坑和反模式
</step>

<step n="6" goal="设计输入整理 → 依赖预检查（硬关口）">
 - 基于第 2-5 步的分析，整理设计阶段必须遵守的目标、约束、已知依赖、风险和设计假设；把每条设计假设写入 `discovery-brief.contract.yaml.design_assumptions[]`（`assumption` + `impact_on`）。
 - 路线影响分支识别方法：什么样的事实 / 约束 / 风险才算「会影响后续实现路线的分支」——满足任一即构成一条分支：同一需求存在多个互斥的技术承载或方案路线（选哪条会改变后续实现）；关键约束尚未确定其取值，而不同取值会导向不同方案选型；风险点一旦成立会推翻或改变方案选型；外部依赖 / 接口的能力或形态未定，其结果会决定走哪条实现路径。不满足上述任一、只是普通待办或细节待补的，不写成分支，只留在对应段的待澄清点。
 - 条件：按上述方法识别出 ≥ 2 条会影响后续实现路线的事实分支、约束分支或风险分支
  - 只记录“路线影响线索”，不得在探索阶段（discovery）要求用户选择技术路线或产品路线。
  - 在 `discovery-brief.md` 按以下约定模板逐条写清每条分支，不能只写分支名：`分支 / 事实来源 / 影响的产品定义或方案判断 / 风险 / 待确认点`。其中「事实来源」必须可核验（任务契约、project-context、现有代码、graphify 证据或文档），无来源的怀疑只能写成待确认点。
  - 这些分支只作为产品定义阶段（PRD）和方案阶段（solution）的输入；若分支会改变任务目标、范围、验收口径或系统责任，回流任务接入 / 产品定义决策，不在探索阶段定路线。
 - 调 `harness discovery check-dependency-trigger --mission <id> --json` 取 `{required, signals[], reasons[]}` typed 判定（基于 mission-contract 关键词 + graphify 索引信号）。

 - 条件：check-dependency-trigger.required=true
 - 执行 `dependency-impact` 技能（读取 `.harness/common/skills/dependency-impact/SKILL.md`），并把产出的 `dependency-impact.md` 作为当前探索任务切片的证据产物。
 - 等待 `dependency-impact.md` 产出并经 `dependency-validity-reviewer` 通过（PASS）；只有命中决策门或检查点时才等待用户确认，然后继续第 8 步。

 - 条件：check-dependency-trigger.required=false
 - 把 CLI 返回的 `reasons[]` 记入 `discovery-brief.contract.yaml.degradations[]` 的 `compensating_action` 字段或简报正文，明确“为何不触发依赖检查”，不得静默跳过。
</step>

- 条件：`agent_engineering.enabled=true`
<step n="7" goal="评估智能体化（Agent 化）机会">
 - 参考 `docs/methodologies/agent-capability-engineering.md` §1（何时使用智能体架构（Agent 架构））
 - 对每个识别出的核心组件，调 `harness discovery agent-eng-eval --mission <id> --component <name> [--autonomy] [--runtime-context] [--multi-step] [--uncertainty] [--notes <text>] --json`。命令把 4 个布尔值写入 `discovery-brief.contract.yaml.agent_engineering_candidates[]`，并按 4-of-4 全为 true → `recommended=agentize`，否则 → `deterministic` 的硬规则裁决。`recommended=agentize` 不允许未达 4-of-4（CLI 直接 reject）。
 - 硬关口：不要为确定性逻辑或简单增删改查（CRUD）建议智能体化（Agent 化）。智能体化必须有明确的自主判断需求，且 4 个布尔字段全为 true。
 </step>

<step n="8" goal="产出 discovery-brief.md + contract.yaml">
 - 调 `harness contract fill --mission <id> --stage discovery --template discovery-brief --artifact harness-runtime/harness/stages/<id>/contracts/discovery-brief.contract.yaml --intent-framing harness-runtime/harness/missions/<id>/intent-framing.yaml --json` 物化契约骨架（如未存在）。然后用 `harness contract patch` 写入第 2-7 步收集的 `affected_capabilities` / `roles` / `scenarios` / `existing_solutions` / `design_assumptions` / `agent_engineering_candidates` / `degradations` 字段。
 - 把人读叙事写入 `harness-runtime/harness/artifacts/<mission-id>/discovery/discovery-brief.md`（沿用 [`harness-runtime/templates/discovery-brief.md`](harness-runtime/templates/discovery-brief.md) 的模板）。结构化字段一律走 `contract.yaml`，不在简报正文内嵌围栏 YAML（fenced YAML）控制契约段。
 - brief 正文段落（仅人读）：
 - 问题空间摘要：核心问题、子问题分解、约束清单
 - 受影响能力（capability）与置信度：引用 `contract.affected_capabilities[]`，简报内一句话总述（不重复结构化字段）
 - 依赖约束：引用 `dependency-impact.md` 结论（Blockers / 高风险不确定项 / 接口兼容性风险）
 - 业务对象候选：候选业务对象、来源证据、状态 / 规则 / 关系线索、命名冲突和需要产品定义阶段（PRD）建模的问题；只给 `business-domain-modeler` 输入，不替产品定义阶段完成业务对象分析
 - 业务用例与系统边界线索：业务目标、关键业务活动、人工 / 当前系统 / 目标系统 / 外部系统责任划分、证据等级和产品定义阶段（PRD）待澄清系统责任；只给 `use-case-modeler` 输入，不替产品定义阶段完成系统用例建模
 - 原型承载线索：可能需要界面（UI）承载的用户任务、业务信息展示、输入、状态 / 错误 / 权限 / 反馈线索；只给交互阶段输入，不替交互阶段决定页面方案
 - 方法与约定：以上三类线索必须包含识别方法和约定模板，不能只写栏目名或对象名清单
 - 用户角色画像：角色表 + 每个角色的关键场景（引用 `contract.roles` / `scenarios`）
 - 现有方案分析：现状、不足、可复用部分（Graphify 证据引用 `contract.existing_solutions[]`）
 - 关键发现：任务契约中没提到但产品定义阶段（PRD）必须考虑的
 - 产品定义阶段（PRD）输入建议：产品定义阶段应该重点覆盖什么、可以简化什么、必须警惕什么
 - 更新 `mission-status`：当前任务切片的 `control_plane.stage`（discovery）标记为 done。
</step>

<step n="9" goal="discovery 有效性审查">
 - 通过 `Task(subagent_type="discovery-effectiveness-reviewer", prompt=<Task Envelope>)` 工具调用 `discovery-effectiveness-reviewer` subagent，输入：当前任务切片的 `discovery-brief.md` 路径、外部 `contracts/discovery-brief.contract.yaml` 路径、`mission-contract.md` 与 `mission-contract.contract.yaml` 路径、`project-context` 与 `project-knowledge/specs` 基线路径。
 - 审查员（reviewer）仅 Read/Grep/Glob；不写简报正文，结论（verdict）通过 `harness-cli` 写入 `contracts/discovery-brief.contract.yaml` 的 `control_contract.role_verdicts`。
 - 无轮次放行（producer_fixable 缺口不设自补上限，`rounds_used` 只记录修复历史，永不构成放行理由，每轮以等同严格度复审）；保持（HOLD）时主流程按每条 `blocking_gaps` 的类别分流：`reasoning_chain_open` / `internal_contradiction` 等产出者可自补（producer_fixable）的缺口，转回第 2-7 步对应段让 discovery-analyst 补；`needs_user_clarification`（结论标 ASSUMED 且信息确实缺失——scope / 系统责任划分 / 覆盖范围无法由 analyst 凭现有证据补齐）不进 analyst 自补循环，走 AskUserQuestion / Decision Gate 人工裁决（类比第 3 步 scope 溢出与第 10 步确认门）。卡死时（同一 producer_fixable 缺口在 analyst 重写后仍以相同根因连续 HOLD 且无实质进展，按缺口本质判断、不是"轮次到点"）不得接受现状降级，重新归因后走 AskUserQuestion 人工裁决（决策候选**不含"接受现状降级"**：强制保持（HOLD）回框定 / 改任务范围 / 升级 BLOCKED）。
 - 条件：审查员结论（reviewer verdict）= 通过（PASS）
  - 继续第 10 步用户确认。
 - 条件：审查员结论 = 保持（HOLD）且 `blocking_gaps` 中存在产出者可自补（producer_fixable，类别为 `reasoning_chain_open` / `internal_contradiction`）的缺口
  - 仅就这些可自补缺口按 `blocking_gaps` 回到对应步骤补充，回第 8 步重写简报，再回本步骤复审（无轮次上限，直到 reviewer 在等同严格度下 PASS 或卡死后按上面归因升级）；不要把 `needs_user_clarification` 缺口塞进本自补回环。
 - 条件：审查员结论 = 保持（HOLD）且 `blocking_gaps` 中存在 `needs_user_clarification`（ASSUMED 且 scope / 系统责任 / 范围信息确实缺失，analyst 无法凭现有证据补齐）
  - 不进 discovery-analyst 自补循环；调用 AskUserQuestion 工具（Claude）/ question tool（OpenCode）/ equivalent 走 Decision Gate（类比第 3 步 scope 溢出门与第 10 步确认门），把缺失信息的类型化候选交用户裁决，按用户回答补齐对应 scope / 系统责任 / 范围结论后回第 8 步重写简报，再回本步骤复审。
 - 条件：审查员结论 = 阻断（BLOCKED）
  - 记录到 `mission-status`，停止探索；按 `SKILL.md` 的失败恢复路径处理。
</step>

<step n="10" goal="与用户确认关键发现">
 - 调 `harness discovery summary --mission <id> --format user --json` 取类型化展示文本（typed display，含按置信度统计的 `affected_capabilities`、按类型统计的 `roles` / `scenarios`、按来源统计的 `existing_solutions`、按建议统计的 `agent_engineering_candidates` 等结构化计数 + 人读展示段）。把展示文本直接展示给用户。
 - 调用 AskUserQuestion 工具（Claude）/ question tool（OpenCode）/ equivalent，提供以下 4 项类型化候选；用户回答的枚举值（enum）写入 `harness approval append --type checkpoint --stage discovery --checkpoint discovery_confirmation --status <approved|rejected|modified> --comment "<enum>: <补充说明>" --json`：
 - `approved`：确认通过（进入第 11 步阶段退出门（stage exit gate）→ 产品定义阶段（prd））
 - `roles_scenarios_missing`：角色 / 场景遗漏（回第 4-5 步补，再回第 8 步重写简报，再回本步骤重新展示摘要）
 - `findings_need_revision`：关键发现 / 智能体化（Agent 化）候选需修订（回第 5-7 步调整，再回第 8 步重写，再回本步骤）
 - `scope_change`：范围需调整（触发 course-correction 技能，本次探索暂停（discovery HALT），不进第 11 步）

 - 条件：用户回答（user answer）= `approved`
  - 进入第 11 步阶段退出门（stage exit gate）。
 - 条件：用户回答 != `approved`
  - 按对应枚举值回滚到正确步骤；保留审批记录（approval）便于复盘（retrospective）追踪。
</step>

<step n="11" goal="探索阶段退出门">
 - 调 `harness gate run --stage discovery --mission <id> --mission-slice harness-runtime/harness/work-graph/mission-slices/<id>.yaml --artifact harness-runtime/harness/artifacts/<id>/discovery/discovery-brief.md --ai-interpretation "<本次 discovery 关键结论一段话>" --json` 跑阶段退出门（stage exit gate），类型化输出供下游消费。
 - 条件：`gate run.status = PASS`
  - 调 `harness mission stage complete --mission <id> --stage discovery --json` 写阶段退出证据；后续由阶段门和看板路由决定工作图推进（discovery → prd）。
 - 条件：`gate run.status = FAIL`
  - 记录关口报告（gate report）路径到 `mission-status`，按 `<failure_paths>

| 失败 | 触发 | 处理 |
|---|---|---|
| `` |  | 当 `harness graphify status` 返回 `available=false` 且本任务是既有项目，必须在 `discovery-brief.contract.yaml.degradations[]` 写入 `kind: graphify_unavailable` 一条，附 `compensating_action`（如 `graphify .` 或手动代码搜索）；该记录缺失时第 9 步审查员直接保持（HOLD）。 |
| `` |  | 第 3 步发现已确认（CONFIRMED）影响面超出任务 `scope_in`：暂停探索，触发 AskUserQuestion / 决策门，候选 4 项（扩范围回任务接入 / 缩方案保 `scope` / 重做任务接入 / 接受现状降级写 `design_assumptions`）；不允许 discovery-analyst 自行选择。 |
| `` |  | 第 6 步触发 `dependency-impact` 后，`dependency-validity-reviewer` 结论（verdict）≠ 通过（PASS）：暂停探索（HALT discovery）；按 dependency-impact 技能的失败恢复路径处理；不得越过该审查员调第 8 步写简报。 |
| `` |  | 第 9 步有效性审查卡死（同一 producer_fixable 缺口在 analyst 重写后仍以相同根因连续保持（HOLD）且无实质进展，按缺口本质判断、非轮次到点；轮次永不构成放行理由）：重新归因后调 AskUserQuestion 走人工裁决（候选**不含"接受现状降级"**：强制保持（HOLD）回框定 / 改任务范围 / 升级 BLOCKED）；裁决后用 `harness approval append --type checkpoint --status approved/rejected` 记录。 |
| `` |  | 第 11 步 `gate run` 失败（FAIL）：按关口报告（gate report）中的失败列表回到对应步骤重做；不得直接调 `harness mission stage complete` 跳过关口。 |
| `` |  | 第 0 步走 `discovery skip` 但任务实际是既有项目（Graphify 索引存在 / 关键词命中）：CLI 不阻止跳过，但复盘阶段（retrospective）会基于 `approvals.json` 的 `discovery_skip` 记录与既有项目信号交叉审视；运行时必须记录跳过理由（CLI 已经强制 `--reason`）。 |

</failure_paths>

</workflow>
