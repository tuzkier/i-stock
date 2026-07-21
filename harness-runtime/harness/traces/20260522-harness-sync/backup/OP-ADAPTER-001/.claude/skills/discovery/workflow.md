# 探索工作流

> **触发条件（何时使用/跳过/HARD-GATE）和行为约束（反合理化）见 `SKILL.md`，不在此重复。**
> **方法论参考**：`.harness/docs/methodology-reference.md` §1（Event Storming — Brandolini；Impact Mapping — Adzic；Jobs-to-be-Done — Christensen）

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用（默认带 `--json`、消费 typed payload、不直接拼 Bash 底层脚本，详见 `.harness/common/skills/harness-cli/SKILL.md`）。

<workflow stage="discovery" version="2">

<goal>
  对问题空间做深度探索，识别隐藏约束、技术风险、信息空白，产出结构化 discovery-brief 给下游 prd / design 使用。
</goal>

<role>
  你先是问题空间侦察者，再是简报作者。先做事实采集（gitnexus 索引 / spec 影响面 / 现有方案 / 用户角色 / Agent 化候选），把每条结论标注证据或推断链，再写人读叙事。不替 prd 设计方案；只发现事实。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `discovery-brief-not-fenced` | discovery-brief.md 不得内嵌 fenced YAML 控制契约段 | cli=harness contract check |
| `discovery-contract-via-cli` | discovery-brief.contract.yaml 由 harness contract fill / patch 写入，agent 不直接 Edit/Write | hook=discovery-check-stage-worktree |
| `reviewer-readonly` | discovery-effectiveness-reviewer 必须在 readonly subagent 中调用（strict_mode 白名单） | registry=subagents/discovery-effectiveness-reviewer[readonly=true,strict_mode=true] |
| `brownfield-gitnexus-evidence` | 棕地任务下 existing_solutions[].source 至少一条 gitnexus_*，或 degradations[] 显式 acknowledge | hook=discovery-check-gitnexus-brownfield<br>cli=harness contract check |
| `spec-coverage` | spec.enabled=true 时 affected_capabilities 必须覆盖 project-knowledge/specs/ 所有 capability | cli=harness contract check |
| `agentize-four-of-four` | recommended=agentize 必须 4 boolean 全 true | cli=harness discovery agent-eng-eval |

</invariants>

<entry>
  - mission-contract 已写入（intake stage 完成）
  - skill-router 判定本消息属 discovery 阶段（或 discovery 在 skippable_stages 中且通过 harness discovery skip 显式跳过）
</entry>

<exit>
  - `brief-written`: discovery-brief.md 写入 discovery stage worktree
  - `contract-filled`: discovery-brief.contract.yaml 已填充且 harness contract check PASS（含 W-spec-coverage / W-discovery-contract / W-gitnexus-source 三规则）
  - `reviewer-pass`: discovery-effectiveness-reviewer PASS 或 max_rounds 用尽后用户裁决记录
  - `user-confirmation`: approvals.json 含 discovery_confirmation 已 approved，或 discovery_skip 已记录
  - `gate-pass`: harness gate run --stage discovery 返回 status=pass
</exit>

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` |  |
| deny | `Edit(harness-runtime/harness/work-graph/**)` |  |
| deny | `Edit(harness-runtime/harness/work-graph/mission-slices/**)` |  |
| deny | `Edit(harness-runtime/harness/work-graph/nodes/**)` |  |
| deny | `Write(harness-runtime/harness/mission-status.yaml)` |  |
| deny | `Write(harness-runtime/harness/work-graph/**)` |  |
| deny | `Bash(git push --force *)` |  |
| deny | `Bash(git push --force-with-lease *)` |  |
| deny | `Bash(git reset --hard *)` |  |
| deny | `Bash(rm -rf /*)` |  |
| ask | `Bash(git checkout -b *)` |  |
| ask | `Bash(git push *)` |  |
| ask | `Bash(git rebase *)` |  |
| ask | `Bash(npx gitnexus analyze*)` |  |
| ask | `Bash(rg *)` |  |
| ask | `Bash(grep *)` |  |
| allow | `Bash(harness *)` |  |
| allow | `Bash(python3 .claude/hooks/**)` |  |
| allow | `Write(harness-runtime/harness/stages/*/discovery-brief.md)` |  |
| allow | `Write(harness-runtime/harness/stages/*/contracts/discovery-brief.contract.yaml)` |  |

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `discovery-analyst` | spawn | harness-runtime/harness/stages/${mission-id}/discovery-brief.md, harness-runtime/harness/stages/${mission-id}/contracts/discovery-brief.contract.yaml | `.harness/common/agents/discovery-analyst.md` |
| `discovery-effectiveness-reviewer` | spawn readonly |  | `.harness/common/agents/discovery-effectiveness-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `project-context.md` | conditional: brownfield | Context |
| `project-knowledge/specs/**` | conditional: spec.enabled=true | Memory |
| `harness.yaml` | true via harness config snapshot | Memory |
| `.gitnexus/` | conditional: brownfield via harness gitnexus status | Context |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `discovery-brief-md` | `harness-runtime/harness/stages/${mission-id}/discovery-brief.md` | markdown | Memory |
| `discovery-brief-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/discovery-brief.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step n="0" goal="进入 discovery stage 并初始化控制面">
 - 通过 harness-cli skill 调用 `harness mission stage start --mission <id> --stage discovery --json`，写入 stage 入栈记录。
 - 调 `harness trace log-init --mission <id> --stage discovery --json` 引导 trace JSONL。
 - 调 `harness context check --json`：PASS 则读 `project-context.md`；FAIL 时按 `project-context` 规则处理并在 discovery-brief evidence 中记录 `inputs_missing.project_context=true`，不得静默继续。
 - 调 `harness config snapshot --json` 读取 `spec.enabled`（决定 Step 3 是否执行）与 `agent_engineering.enabled`（决定 Step 7 是否执行）。不得直接读取 `harness-runtime/config/harness.yaml`。
 - 调 `harness gitnexus status --json` 写入 trace；available=true && fresh=true ⇒ Step 2 可直接走 gitnexus 证据；available=false 或 fresh=false ⇒ Step 2 进入 degradation 路径。
 - 调 `harness frame current --mission <id> --json` 读复杂度、autonomy_level 和 skippable_stages；若 discovery 在 skippable_stages 中且任务为绿地（gitnexus.available=false 且无 trigger keywords），可走 `harness discovery skip --mission <id> --reason <text> --json` 跳过 discovery。
 - 条件：discovery 已跳过
  - 跳到 Step 11 stage exit gate，不进入 Step 1-10。
 - 条件：discovery 不跳过
  - 读取 discovery 阶段 role policy；未配置时默认执行子 Agent 为 `discovery-analyst`；继续 Step 1。
</step>

<step n="1" goal="专业角色调度">
 - 通过 `Task(subagent_type="discovery-analyst", prompt=<Task Envelope>)` 工具调用 `discovery-analyst` subagent，仅追加路径化 Task Envelope；Envelope 只包含：任务目标、输入路径（Mission Contract、project-context 如存在、project-knowledge/specs 索引如启用）、输出路径、write_scope、可用工具（GitNexus/Cognee 可用性只给状态和查询入口，不粘贴大段结果）和事实来源 / 置信度要求。Role prompt 由 install 时物化的 `.<adapter>/agents/discovery-analyst.md` 加载，workflow 内不再复制原文，也不得复述或改写 discovery-analyst 的角色边界。
 - `discovery-analyst` 不负责直接写 Mission Slice、mission-status 或控制面 YAML；它只写 discovery-brief 并返回 DONE / BLOCKED 与执行结果建议摘要。主流程负责登记 evidence 和状态。
</step>

<step n="2" goal="问题空间分析">
 - 从任务契约出发，分析：

 **当前现状**
 - 现在的流程/系统是怎样的（棕地项目从代码库和 project-context 分析）
 - 谁在用、怎么用、痛点在哪

 - 条件：棕地=true 或任务明确要求项目/代码/架构/调用链/执行流分析
 - HARD-GATE：调 `harness gitnexus status --json` 读 `{available, indexed, fresh}`。available=true && fresh=true 时继续走 gitnexus 证据路径；否则强制把对应 `gitnexus_unavailable` / `gitnexus_stale` 一条写入 `discovery-brief.contract.yaml.degradations[]`（缺该记录时 Step 9 reviewer 会 HOLD）。
 - 使用 `gitnexus-exploring` 建立现有代码事实：
 - READ `gitnexus://repos`，确认目标仓库是否已索引
 - READ `gitnexus://repo/{name}/context`，记录索引新鲜度和代码库概览
 - `gitnexus_query({query: "<本次 Mission 相关概念>"})`，定位相关模块和执行流
 - 对关键符号执行 `gitnexus_context({name: "<symbol>"})`，确认调用关系
 - 将 GitNexus 证据写入 `discovery-brief.contract.yaml.existing_solutions[]`（source = gitnexus_symbol / gitnexus_query，reference = gitnexus 路径），并在 brief 正文「现有方案分析」段引用。
 - 条件：GitNexus 不可用 / 未索引 / 索引过期
 - 记录降级原因，不得静默回退
 - 给出补救动作，例如 `npx gitnexus analyze`；再用手动代码搜索作为临时证据

 **问题拆解**
 - 核心问题是什么（不是表面症状，是根因）
 - 核心问题可以拆成哪几个子问题
 - 哪些子问题是本次任务要解决的，哪些不是

 **约束识别**
 - 技术约束（从 project-context和现有代码）
 - 业务约束（从任务契约的 constraints）
 - 时间/资源约束
</step>

- 条件：spec.enabled=true
 <step n="3" goal="识别受影响能力（规格基线对照）">
 <!--
 探索的核心产出之一：回答「本次任务会碰到项目行为契约的哪些部分」。
 结论将作为 PRD Step 7 产出差量规格的能力来源。
 -->
 - 先调 `harness spec scan --mission <id> --scope-in <path1> --scope-in <path2> --json` 取候选 capability 列表（CLI 用 capability 名 vs scope_in 子串匹配自动给出 CONFIRMED / ASSUMED 初判）。
 - 对每个候选 capability 读取其 `spec.md` 中的 Requirement 清单，把 CLI 初判升级为最终 confidence：

 | 判断 | 置信度 | 写入方式 |
 |------|------|---------|
 | 有规格文本直接对应任务契约的 scope_in | **CONFIRMED** | 标注引用的 Requirement 名 + 基线规格路径 |
 | 基于架构/依赖推断会影响，但无直接规格文本证据 | **UNCERTAIN** | 标注推断链路（为什么怀疑会影响） |
 | 完全不在规格中但任务明显涉及（新能力） | **ASSUMED**（新建） | 标注「本任务将首次为 `<capability>` 建立规格」 |

 - Hard gate：不允许把置信度当摆设。每条必须有证据或推断链，不能写"可能"、"大概"。

 - 把结论写入 `discovery-brief.contract.yaml.affected_capabilities[]`（每条：capability / requirement_id / confidence / evidence_or_inference）；不在 brief 正文内嵌 fenced YAML，brief 只保留人读叙事。

 - 条件：发现 CONFIRMED 或高置信 UNCERTAIN 的影响面显著超出任务契约的 scope_in
 - HALT discovery；调用 AskUserQuestion 工具（Claude）/ question tool（OpenCode）/ equivalent，提供以下 4 项 typed 候选（用户回答的 enum 值写入 `harness approval append --type checkpoint --stage discovery --checkpoint discovery_scope_overflow --status approved --comment "<enum>" --json`）：
 - `expand_scope`：扩范围（回 intake 重写 mission-contract scope_in；本次 discovery HALT 不写 brief）
 - `shrink_solution`：缩方案（保 scope 不变，调整 discovery 输出仅覆盖 scope_in 内）
 - `redo_intake`：重做 intake（mission contract 重写，整个 mission 回 Stage 1）
 - `accept_degradation`：接受现状降级（把超 scope 的 capability 标 ASSUMED + 记入 `design_assumptions[].impact_on=prd`）
 - 不允许 discovery-analyst 自行选择；得到用户 enum 回答后按对应路径继续或回滚。
 </step>

<step n="4" goal="用户角色与场景分析">
 - 识别所有相关的用户角色：

 | 角色 | 核心诉求 | 使用频率 | 技术水平 |
 |------|---------|---------|---------|
 | | | | |

 - 为每个角色识别关键场景：
 - 主要使用场景（Happy Path）
 - 异常场景
 - 边界场景（首次使用、极端数据、权限不足）
</step>

<step n="5" goal="现有方案调研">
 - 分析当前的解决方案（如果有）：
 - 现有方案为什么不够好
 - 现有方案哪些部分可以复用
 - 现有方案的用户反馈（如果可获取）

 - 条件：存在现有代码方案且 gitnexus-exploring 可用
 - 用 GitNexus 查相关执行流和模块边界，避免只凭目录名或 grep 推断架构
 - 至少记录：相关 cluster/process、关键符号、调用关系、可复用点和风险点

 - 如果是全新领域，分析：
 - 同类产品/功能的常见做法
 - 行业最佳实践
 - 已知的坑和反模式
</step>

<step n="6" goal="设计输入整理 → 依赖预检查（HARD-GATE）">
 - 基于 Step 2-5 的分析，整理设计阶段必须遵守的目标、约束、已知依赖、风险和设计假设；把每条设计假设写入 `discovery-brief.contract.yaml.design_assumptions[]`（assumption + impact_on）。
 - 条件：发现 ≥ 2 条实质可行路线且会显著影响依赖检查或 PRD 边界
  - 调用 AskUserQuestion 工具（Claude）/ question tool（OpenCode）/ equivalent，提供路线候选 typed 数组 `[{id, description, impact, risk}, ...]`，由用户选定 id。回答写入 `harness approval append --type tradeoff --stage discovery --checkpoint route_selection --status approved --comment "<chosen_route_id>" --json`。
  - 未得到用户回答前不得继续 Step 6 后续动作（保持 discovery HALT）。
 - 调 `harness discovery check-dependency-trigger --mission <id> --json` 取 `{required, signals[], reasons[]}` typed 判定（基于 mission-contract 关键词 + gitnexus 索引信号）。

 - 条件：check-dependency-trigger.required=true
 - 执行 `dependency-impact` 技能（读取 .harness/common/skills/dependency-impact/SKILL.md），并把产出的 `dependency-impact.md` 作为当前 discovery Mission Slice 的 evidence artifact。
 - 等待 `dependency-impact.md` 产出并经 `dependency-validity-reviewer` PASS；只有命中 Decision Gate 或 Checkpoint 时才等待用户确认，然后继续 Step 8。

 - 条件：check-dependency-trigger.required=false
 - 把 CLI 返回的 reasons[] 记入 `discovery-brief.contract.yaml.degradations[]` 的 compensating_action 字段或 brief 正文，明确"为何不触发依赖检查"，不得静默跳过。
</step>

- 条件：`agent_engineering.enabled=true`
 <step n="7" goal="评估 Agent 化机会">
 - 参考 `docs/methodologies/agent-capability-engineering.md` §1（何时使用 Agent 架构）
 - 对每个识别出的核心组件，调 `harness discovery agent-eng-eval --mission <id> --component <name> [--autonomy] [--runtime-context] [--multi-step] [--uncertainty] [--notes <text>] --json`。命令把 4 个布尔写入 `discovery-brief.contract.yaml.agent_engineering_candidates[]`，并按 4-of-4 全 true → recommended:agentize / 否则 → deterministic 的硬规则裁决。`recommended=agentize` 不允许未达 4-of-4（CLI 直接 reject）。
 - Hard gate：不要为确定性逻辑或简单 CRUD 建议 Agent 化。Agent 化必须有明确的自主判断需求，且 4 个布尔字段全 true。
 </step>

<step n="8" goal="产出 discovery-brief.md + contract.yaml">
 - 调 `harness contract fill --mission <id> --stage discovery --template discovery-brief --artifact harness-runtime/harness/stages/<id>/contracts/discovery-brief.contract.yaml --intent-framing harness-runtime/harness/missions/<id>/intent-framing.yaml --json` 物化 contract 骨架（如未存在）。然后用 `harness contract patch` 写入 Step 2-7 收集的 affected_capabilities / roles / scenarios / existing_solutions / design_assumptions / agent_engineering_candidates / degradations 字段。
 - 把人读叙事写入 `harness-runtime/harness/stages/<mission-id>/discovery-brief.md`（沿用 [`harness-runtime/templates/discovery-brief.md`](harness-runtime/templates/discovery-brief.md) 的模板）。结构化字段一律走 contract.yaml，不在 brief 正文内嵌 fenced YAML 控制契约段。
 - brief 正文段落（仅人读）：
 - 问题空间摘要：核心问题、子问题分解、约束清单
 - 受影响 capability 与置信度：引用 contract.affected_capabilities[]，brief 内一句话总述（不重复结构化字段）
 - 依赖约束：引用 `dependency-impact.md` 结论（Blockers / 高风险不确定项 / 接口兼容性风险）
 - 用户角色画像：角色表 + 每个角色的关键场景（引用 contract.roles / scenarios）
 - 现有方案分析：现状、不足、可复用部分（gitnexus 证据引用 contract.existing_solutions[]）
 - 关键发现：任务契约中没提到但 PRD 必须考虑的
 - PRD 输入建议：PRD 应该重点覆盖什么、可以简化什么、必须警惕什么
 - 更新 mission-status：当前 Mission Slice 的 `control_plane.stage`（discovery）标记为 done。
</step>

<step n="9" goal="discovery 有效性审查">
 - 通过 `Task(subagent_type="discovery-effectiveness-reviewer", prompt=<Task Envelope>)` 工具调用 `discovery-effectiveness-reviewer` subagent，输入：当前 Mission Slice 的 `discovery-brief.md` 路径、外部 `contracts/discovery-brief.contract.yaml` 路径、`mission-contract.md` 与 `mission-contract.contract.yaml` 路径、project-context 与 project-knowledge/specs 基线路径。
 - reviewer 仅 Read/Grep/Glob；不写 brief 正文，verdict 通过 `harness-cli` 写入 `contracts/discovery-brief.contract.yaml` 的 `control_contract.role_verdicts`。
 - rounds_used 上限 3；HOLD 时主流程把 blocking_gaps 转回 Step 2-7 对应段，让 discovery-analyst 补；max_rounds 用尽走 AskUserQuestion 走人工裁决（决策候选：接受现状降级 / 强制 HOLD 回 framing / 改 mission scope）。
 - 条件：reviewer verdict = PASS
  - 继续 Step 10 用户确认。
 - 条件：reviewer verdict = HOLD 且 rounds_used &lt; 3
  - 按 blocking_gaps 回到对应步骤补充，回 Step 8 重写 brief，再回本 step 复审。
 - 条件：reviewer verdict = BLOCKED
  - 记录到 mission-status，停止 discovery；按 SKILL.md 的失败恢复路径处理。
</step>

<step n="10" goal="与用户确认关键发现">
 - 调 `harness discovery summary --mission <id> --format user --json` 取 typed display 文本（含 affected_capabilities by confidence / roles / scenarios by kind / existing_solutions by source / agent_engineering_candidates by recommendation 等结构化计数 + 人读 display 段）。把 display 直接展示给用户。
 - 调用 AskUserQuestion 工具（Claude）/ question tool（OpenCode）/ equivalent，提供以下 4 项 typed 候选；用户回答的 enum 值写入 `harness approval append --type checkpoint --stage discovery --checkpoint discovery_confirmation --status <approved|rejected|modified> --comment "<enum>: <补充说明>" --json`：
 - `approved`：确认通过（进入 Step 11 stage exit gate → prd）
 - `roles_scenarios_missing`：角色 / 场景遗漏（回 Step 4-5 补，再回 Step 8 重写 brief，再回本 step 重新展示 summary）
 - `findings_need_revision`：关键发现 / Agent 化候选需修订（回 Step 5-7 调整，再回 Step 8 重写，再回本 step）
 - `scope_change`：范围需调整（触发 course-correction skill，本次 discovery HALT 不进 Step 11）

 - 条件：user answer = approved
  - 进入 Step 11 stage exit gate。
 - 条件：user answer != approved
  - 按对应 enum 回滚到正确 step；保留 approval 记录便于 retrospective 追踪。
</step>

<step n="11" goal="Discovery stage exit gate">
 - 调 `harness gate run --stage discovery --mission <id> --mission-slice harness-runtime/harness/work-graph/mission-slices/<id>.yaml --artifact harness-runtime/harness/stages/<id>/discovery-brief.md --ai-interpretation "<本次 discovery 关键结论一段话>" --json` 跑 stage exit gate，typed 输出消费下游。
 - 条件：gate run.status = PASS
  - 调 `harness mission stage complete --mission <id> --stage discovery --json` 写 stage exit evidence；后续由 Stage Gate / Board Router 决定 Work Graph 推进（discovery → prd）。
 - 条件：gate run.status = FAIL
  - 记录 gate report 路径到 mission-status，按 `<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `` |  | 当 `harness gitnexus status` 返回 available=false 且本任务是棕地，必须在 `discovery-brief.contract.yaml.degradations[]` 写入 `kind: gitnexus_unavailable` 一条，附 `compensating_action`（如 `npx gitnexus analyze` 或 手动代码搜索）；该记录缺失时 Step 9 reviewer 直接 HOLD。 |
| `` |  | Step 3 发现 CONFIRMED 影响面超 mission scope_in：HALT discovery，触发 AskUserQuestion / Decision Gate，候选 4 项（扩范围回 intake / 缩方案保 scope / 重做 intake / 接受现状降级写 design_assumptions）；不允许 discovery-analyst 自行选择。 |
| `` |  | Step 6 dependency-impact 触发后 `dependency-validity-reviewer` verdict ≠ PASS：HALT discovery；按 dependency-impact skill 的失败恢复路径处理；不得越过该 reviewer 调 Step 8 写 brief。 |
| `` |  | Step 9 effectiveness review rounds_used 用尽（上限 3）仍 HOLD：调 AskUserQuestion 走人工裁决（接受现状降级 / 强制 HOLD 回 framing / 改 mission scope）；裁决后用 `harness approval append --type checkpoint --status approved/rejected` 记录。 |
| `` |  | Step 11 gate run FAIL：按 gate report 中的 FAIL 列表回到对应 Step 重做；不得直接调 `harness mission stage complete` 跳过 gate。 |
| `` |  | Step 0 走 `discovery skip` 但任务实际是棕地（gitnexus 索引存在 / 关键词命中）：CLI 不阻止跳过，但 retrospective 阶段会基于 approvals.json `discovery_skip` 记录与 brownfield 信号交叉审视；运行时必须记录跳过理由（CLI 已经强制 `--reason`）。 |

</failure_paths>

</workflow>
