# 验证工作流

> **行为约束（铁律、禁用词、验证门控、反合理化）见 `SKILL.md`，不在此重复。**
> **方法论参考**：`.harness/docs/methodology-reference.md` §10（测试金字塔（Test Pyramid）；测试奖杯（Testing Trophy）；契约测试（Contract Testing）；性质测试（Property-Based Testing））§12（使用率 / 饱和度 / 错误率方法（USE Method）；请求率 / 错误率 / 时延方法（RED Method））

所有命令行接口（CLI）调用通过 `harness-cli` 技能（`--json` 模式）。

<workflow stage="verify" version="2">

<goal>
  对执行和代码审查产物逐条验证 `SUC-xx-OP-xx` 系统操作以及验收场景 / 条件的“预期结果 / 实际结果”，收集命令证据和结果证据，产出 `verification-report.md`、`verification-report.contract.yaml` 和四态结论：通过、失败、阻塞、带风险通过。
</goal>

<role>
  你是验证编排者。你调度验证工程师（verification-engineer）建立验证模型并收集证据，调度验证有效性审查员（verification-effectiveness-reviewer）审查证据充分性；每条验收场景 / 条件必须绑定命令证据和结果证据。不得把测试通过等同于验收通过，不得在验证阶段直接修改实现文件。
</role>

<stage_capability>

验证阶段对应 RUP 测试工作流。它的核心能力不是“再跑一遍测试”，而是回答“当前增量的验收场景 / 条件是否已经被可复现、可观察、可审查的证据真实证明”。

| 能力 | 本阶段必须判断什么 | 失败时 |
|---|---|---|
| 输入合格性判断 | 任务契约、产品定义包、交互产物、技术分析、执行简报、代码审查和项目测试约定是否足以建立验证依据 | BLOCKED，回上游补依据 |
| 验证模型判断 | 每个 `SUC-xx-OP-xx` 和每条验收场景 / 条件是否有来源、预期结果、实际观察方式、验证动作、失败判定和回流建议 | HOLD，不得先跑命令倒推结论 |
| 证据规划判断 | 命令证据和结果证据是否绑定执行简报 required_evidence，且覆盖系统操作、验收场景 / 条件、质量与运行约束和高优先级风险 | HOLD，回执行补证据义务或补验证计划 |
| 命令证据判断 | 验证动作是否在当前上下文真实运行，命令、工作目录、退出码、报告和失败输出是否可复现 | HOLD 或 BLOCKED |
| 结果证据判断 | 实际结果是否来自用户、调用方、命令行使用者或运维者可观察的结果，而不是测试通过、代码阅读或执行者自述 | HOLD，补真实结果证据 |
| 验收结论判断 | 通过 / 失败 / 阻塞 / 带风险通过是否与预期结果、实际结果、命令证据、结果证据和审查状态一致 | 失败路径路由，不得改写结论 |
| 风险与质量约束判断 | 质量与运行约束、方案风险和技术分析风险是否已验证、接受、阻断或回流 | HOLD 或 Decision Gate |
| 验证有效性判断 | 验证有效性审查员是否确认验证模型和证据链足以支撑结论 | 不得进入交付 |
| 交付交接判断 | verification-report 是否清楚列出通过项、失败项、阻塞项、带风险项、未覆盖范围和交付判断依据 | 不得完成 verify |

</stage_capability>

<invariants>

| 标识 | 检查 | 执行者 |
|---|---|---|
| `report-contract-via-cli` | `verification-report.contract.yaml` 不得被智能体（Agent）直接写入或编辑，必须经 `harness contract init/patch` | hook=verify-check-contract-via-cli |
| `report-not-fenced` | `verification-report.md` 不得内嵌围栏式 YAML、`evidence_contract`、`execution_result` 或 `role_verdicts` 段 | hook=harness-lint |
| `required-evidence-id-from-upstream` | `command_evidence` / `result_evidence` 的 `required_evidence_id` 必须引用拆解阶段 `execution-brief` 的 `required_evidence[].id`，验证阶段不得自创 | hook=verify-check-evidence-id-referenced |
| `reviewer-readonly` | 验证有效性审查员必须以只读子智能体调用 | registry=subagents/verification-effectiveness-reviewer[readonly=true] |
| `no-impl-edit-in-verify` | 验证阶段不直接修改实现文件或测试文件，失败路径回流缺陷修复或执行阶段 | hard_gate=failure-path-routing |
| `true-e2e-primary-evidence` | 界面验收场景 / 条件通过时必须有真实浏览器路径的主要结果证据；接口、模拟、数据库或内部状态只能作为准备或交叉检查证据 | cli=harness verify true-e2e-check |

</invariants>

<entry>
  - 执行和代码审查已完成，对应产物通过阶段门
  - 当前任务切片的 `control_plane.stage=verify`
</entry>

<exit>
  - `report-written`: `verification-report.md` 已写入验证阶段目录
  - `contract-filled`: `verification-report.contract.yaml` 已填充且 `harness contract check` 通过
  - `ac-trace-complete`: 每条通过的验收场景 / 条件同时引用命令证据和结果证据；阻塞项写明原因、影响和下一步
  - `reviewer-pass`: 验证有效性审查员已审查证据充分性
  - `gate-pass`: `harness verify gate run` 返回通过状态
</exit>

<subagents>

| 角色 | 模式 | 范围 / 约束 | 角色包 |
|---|---|---|---|
| 验证工程师（verification-engineer） | spawn | `harness-runtime/harness/artifacts/${mission-id}/verify/verification-report.md` | `.harness/common/agents/verification-engineer.md` |
| 验证有效性审查员（verification-effectiveness-reviewer） | 只读 spawn | 禁用工具：Edit、Write、MultiEdit、NotebookEdit、Bash | `.harness/common/agents/verification-effectiveness-reviewer.md` |

</subagents>

<inputs>

| 引用 | 是否必需 | 用途 |
|---|---|---|
| `mission-contract.md` | 是 | 读取目标、成功标准、验收条件和范围 |
| `product-definition.md` | 条件：存在产品定义时必读 | 读取系统责任、用例、场景、质量与运行约束和验收口径 |
| `product/use-case-model.md` | 条件：存在产品定义时必读 | 读取业务用例、已确认系统用例、`SUC-xx-FLOW-xx` 流步骤、`SUC-xx-OP-xx` 系统操作和界面承载要求 |
| `product/acceptance-scenarios.md` | 条件：存在产品定义时必读 | 读取验收场景 / 条件和下游追溯锚点 |
| `interaction.md` / `interaction-spec/` | 条件：界面或交互任务必读 | 读取用户路径、界面状态和端到端验证义务 |
| `tech-design.md` | 条件：存在技术分析时必读 | 读取系统操作到技术设计映射、验证策略、架构风险、接口和数据验证要求 |
| `execution-brief.md` | 是 | 读取任务、授权范围、必需证据和停止条件 |
| `code-review.md` | 条件：代码审查已完成时必读 | 读取发现项、修复状态和已接受风险 |
| `project-context.md` | 条件：既有项目必读 | 读取项目测试约定和运行环境约束 |
| `harness.yaml` | 是，通过 `harness config snapshot` 读取 | 读取项目验证配置 |

</inputs>

<outputs>

| 产物 | 路径 | 类型 | 校验方式 |
|---|---|---|---|
| 验证报告 | `harness-runtime/harness/artifacts/${mission-id}/verify/verification-report.md` | Markdown 文档 | 人读产物，必须引用外部契约 |
| 验证报告契约 | `harness-runtime/harness/stages/${mission-id}/contracts/verification-report.contract.yaml` | YAML 契约 | `harness contract check` |

</outputs>

<method>

验证阶段必须先建立“验证模型”，再运行命令。验证模型不是控制面字段，而是验证阶段的专业工作方法；它定义本轮要验证什么、凭什么判断、用什么层次证明、无法证明时回到哪里。

| 方法项 | 具体做法 | 产物落点 |
|---|---|---|
| 验证依据目录 | 汇总任务契约、产品定义、用例模型、验收场景、交互产物、技术分析、执行简报、代码审查和项目测试约定；逐项标明本阶段消费了哪些系统操作、验收场景 / 条件、质量与运行约束、风险和必需证据。 | `verification-report.md` 的“验证依据目录” |
| 系统操作覆盖矩阵 | 每个 `SUC-xx-OP-xx` 必须对齐来源流步骤、预期读写 / 状态迁移、错误 / 补偿 / 幂等、技术设计落点、执行任务和证据。 | `verification-report.md` 的“系统操作覆盖与自洽矩阵” |
| 验收判定卡片 | 每条验收场景 / 条件必须写明来源、预期结果、实际可观察结果、验证动作、命令证据、结果证据、失败判定和回流建议。 | `verification-report.md` 的“验收判定矩阵” |
| 验证层次选择 | 按风险和交付形态选择单元、集成、端到端、非功能、人工验收或智能体（Agent）能力评估；说明为什么这些层次足够，哪些层次不适用。 | `verification-report.md` 的“验证方法” |
| 风险验证计划 | 对方案和技术分析遗留的高优先级风险，说明用哪类证据证明风险已消灭、已接受、被阻断或需要回流。 | `verification-report.md` 的“风险与质量约束验证” |
| 无法验证项处理 | 不能验证时不得改写预期结果；必须标明缺口、影响、下一步和回流目标。 | `verification-report.md` 的“未覆盖范围” |
| 验证评价摘要 | 最后判断证据是否足以支撑交付：通过项、失败项、阻塞项、带风险项分别列出。 | `verification-report.md` 的“验证评价摘要” |

验证层次选择规则：

| 需求类型 | 主要结果证据 | 辅助证据 | 不能单独作为通过依据 |
|---|---|---|---|
| 界面和用户路径 | 真实浏览器路径的界面状态、截图、视频、追踪或可访问性快照 | 接口响应、数据库状态、日志 | 单元测试、模拟响应、内部状态 |
| 接口能力 | 请求、响应、状态码、关键字段、错误语义、权限上下文 | 单元测试、契约测试、日志 | 只有状态码成功 |
| 命令行 / 文件 / 配置 | 命令输出、文件差异、生成物、复现步骤 | 单元测试、静态检查 | 只有命令退出码为 0 |
| 数据、迁移和后台任务 | 数据状态、不变量、迁移前后对照、恢复结果 | 日志、指标、抽样检查 | 只有任务启动成功 |
| 质量与运行约束 | 性能、安全、兼容性、可观测性或可维护性对应的运行结果 | 静态检查、设计说明 | 只有功能测试通过 |
| 智能体能力 | 评估场景、工具调用记录、失败路径、边界约束命中结果 | 人工审查、日志 | 只有提示词说明或智能体自述 |

</method>

<steps>

<step id="step-0" n="0" goal="阶段进入 + 追踪初始化 + 验证范围预计算">
 - 命令行优先预检（CLI-first preflight，用于验证 / 继续 / 状态（verify / continue / status）场景）：调用 `harness control status --json`、`harness control candidates --intent continue --json`；显式确定任务后再调用 `harness control frame --json`、`harness control guidance --json`、`harness control context-index --mission ${mission-id} --json`；指引指向缺少产物、审查、阶段门或批准记录时先处理；临时读取旧文件时记录 `fallback_used`、`fallback_reason`、`legacy_source` 和 `follow_up`。
 - 读取任务契约（验收条件）、产品定义（系统责任、用例、`SUC-xx-OP-xx` 系统操作、场景、质量与运行约束）、用例模型、验收场景、交互产物（用户路径和界面状态，若存在）、技术分析（系统操作到技术设计映射、验证策略和风险验证方式，若存在）、执行简报（系统操作覆盖、任务项清单、变更文件、必需证据三元组）、代码审查（如存在，读取发现项状态）、项目上下文（测试约定，调用 `harness context check`），并调用 `harness knowledge resolve --stage verify --json` 获取规格、测试模式、验证运行手册和经验。
 - 调用 cli `harness mission stage start` `--stage verify --mission ${mission-id}`，evidence=required。
 - 调用 cli `harness trace log-init` `--mission ${mission-id} --stage verify`，evidence=required。
 - 调用 cli `harness verify compute-scope` `--mission ${mission-id}`，evidence=required。
 - 消费 `compute-scope` 返回的 `acceptance_list`、`task_list`、`test_layers`、`e2e_obligations`、`project_lint_enabled` 和 `required_evidence_matrix`。`required_evidence_matrix` 是从执行简报透传的拆解阶段必需证据三元组，是 `command_evidence` / `result_evidence` 的 `required_evidence_id` 查表基准；验证阶段不得自创 `required_evidence_id`。
 - 检查 `compute-scope` 返回的 `execute_failure_ref`；若执行阶段已失败（停止事件命中、授权路径越界、命令证据结果为失败），直接进入 `blocked-execute-failure` 失败路径，不重跑双证据校验。
 - **前端工程路线感知（frontend_engineering）**：如果 `harness config snapshot` 的 `prototype.delivery_mode=frontend_engineering`：
   - 读取上游 `contracts/prototype-as-frontend.contract.yaml`（交互阶段产物）的 `e2e_obligation[]`（兼容旧 key `e2e_locator_obligations[]`）和 `api_contract_draft.endpoints[]` 作为验证范围基线。
   - 本阶段是该路线下“真实后端端到端验证 + 验收场景 / 条件验证”的统一落点；交互阶段只做走查（walkthrough），不把针对模拟服务的运行当作交付证据。
   - Playwright 端到端验证必须连接真实后端运行；模拟服务（MSW）在本阶段不作为主要证据。
   - **门 B（可达性下沉 E2E，以 PRD 流步骤全集为键）**：读 `e2e_obligation[]` 与 PRD 流步骤全集（`use-case-model.md` 的 `SUC-xx-FLOW-xx`），对每条流步骤逐条核验“有 E2E 通过”或“显式 `status: accepted_alternative` + 非空 `accepted_reason`”；缺一即 FAIL。判定与缺口清单来自 `e2e_resolver` 的 `frontend_flowstep_obligations.uncovered_flowsteps`（非空时 resolver status=FAIL、`decision_gate_reasons` 含 `frontend_flowstep_e2e_uncovered`）。
   - 上游契约的 `downstream_handoff.verify[]` 段作为必需证据清单。
 - **默认交互原型路线感知（interactive_prototype）**：如果 `harness config snapshot` 的 `prototype.delivery_mode=interactive_prototype`（默认路线）且本 mission 有 interaction 原型产物（存在 behavior-graph，界面 SSOT）时：
   - 读取交互阶段产出的 behavior-graph（界面 SSOT）作为验证范围基线：edge 的 `e2e_obligation`(bool) + `testid`（e2e 断言锚点，须命中原型 data-testid）、step 的 acceptance_refs、page_state 的 state（loading/empty/error/readable…）+ anchor_root。
   - 本阶段必须为每个 UI 验收场景建立“原型对齐”验证义务：实现的页面 / 状态 / 流程逐项对照 behavior-graph 核对（页面对 page_state、状态结局对 state、流步骤对 edge/step），并以 E2E run 作为结果证据。verification-engineer 必须在 UI 场景的 `result_evidence` 里显式记录断言命中的 behavior-graph `testid`（优先显式 `testids[]` 字段，自由文本子串命中只作兜底），否则下游对齐门会漏判。
   - 这是镜像前端工程路线“门 B（可达性下沉 E2E）”的对称闭环：默认交互原型路线下，UI 任务的 e2e 必须断言对齐 behavior-graph——要么为每条 `e2e_obligation=true` 的 edge 绑定通过的 e2e 断言，要么经决策门把该 edge 登记为 N/A 豁免（`prototype_coverage_exemptions:[{id,reason}]`，理由非空），禁止“实现了但没人验证界面对不对”。
   - 非破坏：非 UI 任务 / 未跑 interaction（无 behavior-graph）时本义务自动跳过。
</step>

<step id="step-1" n="1" goal="建立验证模型">
 - 在运行任何测试之前，先写出本轮验证模型草案。验证模型必须来自上游产物，不得由验证阶段重新定义需求。
 - 建立“验证依据目录”：逐项列出任务契约、产品定义、用例模型、验收场景、交互产物、技术分析、执行简报、代码审查和项目上下文中被本轮验证消费的内容；每一项都写明用途，例如系统操作验证、验收判定、质量与运行约束、风险验证、执行证据或环境约束。
 - 建立“验收判定矩阵”：每条验收场景 / 条件至少包含来源、预期结果、实际观察方式、验证动作、所需命令证据、所需结果证据、失败判定、回流建议。
 - 建立“系统操作覆盖与自洽矩阵”：每个本轮范围内的 `SUC-xx-OP-xx` 必须列出来源 `SUC-xx-FLOW-xx`、预期读取 / 写入 / 状态迁移、错误 / 补偿 / 幂等、技术设计落点、执行任务和证据；缺失则相关验收不得通过。
 - 建立“风险与质量约束验证计划”：对高优先级风险和质量与运行约束写明验证层次、验证方法、通过标准和不能验证时的处理方式。
 - 建立“验证层次选择表”：说明每条验收场景 / 条件为什么使用单元、集成、端到端、质量验证、人工验收或智能体能力评估；如果某层不适用，必须写明理由。
 - 若发现系统操作没有证据覆盖、验收场景 / 条件没有明确预期结果、交互路径缺失、技术分析没有验证策略、执行简报缺必需证据或代码审查存在未关闭高严重级别发现，先记录为验证阻断或回流建议，不得继续把命令成功解释为通过。
</step>

<step id="step-2" n="2" goal="专业角色调度">
 - 调用 cli `harness verify dispatch-worker` `--mission ${mission-id}`，evidence=required。
 通过 `@verification-engineer` native delegation调用 `verification-engineer` subagent（Cursor auto-routes 到对应 agent registry 项）
 - 任务信封：任务契约中的验收条件、产品定义用例、系统操作和质量与运行约束、验收场景、交互路径、技术分析验证策略、执行简报证据义务（含 `required_evidence` 三元组）、代码审查证据、验证模型草案、命令证据路径和结果证据路径；外部契约必须写入 `execution_result`；`command_evidence[].required_evidence_id` 和 `result_evidence[].required_evidence_id` 必须引用拆解阶段 `required_evidence[].id`，不得自创标识。证据角色必须区分 `primary` 与 `cross_check`，避免只用单一命令输出替代结果证据。
 - 调用 cli `harness verify dispatch-reviewer` `--mission ${mission-id}`，evidence=required。
 通过 `@verification-effectiveness-reviewer` native delegation调用 `verification-effectiveness-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
 - 任务信封：验证报告路径、外部验证契约路径、验证模型、命令证据路径、结果证据路径、验收场景 / 条件追踪、证据图切片路径；拒绝主智能体兜底自动通过；审查结论由审查员返回 `role_verdict`，主流程经 `harness contract add-verdict` 写入 `role_verdicts`。
 - 条件：`role_verdict` 含 HOLD（验证有效性审查员判定验证模型或证据链不足以支撑结论，含完备性 / 自洽性缺口类别）
  - 不得把 HOLD 解释为通过，也不得在主流程兜底改写结论。按 HOLD 指出的缺口类型路由到缺口失败路径：证据缺失 / 不足 → 调 `harness verify failure-path --kind execute` 回执行补命令证据与结果证据；实现缺陷类缺口 → 调 `harness verify failure-path --kind bug_fix` 走缺陷修复协议；验证模型缺口（覆盖矩阵 / 验收判定卡片不完备或自相矛盾）→ 回步骤 1 重建验证模型后补证据。
  - 修复后必须重新 `dispatch` 验证有效性审查员（verification-effectiveness-reviewer）对修复结果重审，并经 `harness contract add-verdict` 覆盖写入新的 `role_verdicts`；不得复用上一轮 HOLD 之前的结论或跳过重审。
  - 这一“HOLD → 修复 → 重审”循环无轮次放行：轮次只记录修复历史，永不构成把 HOLD 转为通过的理由，每轮以与首审等同的严格度重审。卡死时（同一 HOLD 在修复后仍以相同根因连续返回且无实质进展，按缺口本质判断、不是"轮次到点"）不得降级通过，发起决策门（调 `harness verify failure-path --kind decision_gate` 并 `harness approval append --type risk --stage verify` 记录用户决策），候选仅含：扩大修复范围继续修 / 缩小交付范围（改 scope）/ 升级 BLOCKED，**不含"接受受限验证 / 降级通过"**。残留风险只能由用户在充分披露未覆盖 / 未通过项后于 Decision Gate 显式拥有并记 approval；无批准记录不得进入步骤 8 的产物门，验证循环本身永不把 HOLD 自动转为通过。
</step>

<step id="step-3" n="3" goal="识别验证范围">
 - 以步骤 0 的 `compute-scope` 返回的 `acceptance_list`、`task_list` 和 `test_layers` 为权威输入，结合步骤 1 的验证模型补充人工解释。确认测试层级：单元（`harness verify run-tests --layer unit`）、集成（`--layer integration`）、端到端验证（`harness verify e2e-status`）。项目上下文没有测试命令时，检测项目测试框架并推导命令。
 - 条件：e2e.enabled=true
  - 检查执行简报是否存在显式端到端验证义务（`e2e_obligation`）；缺失时由端到端解析器根据验收场景 / 条件、界面承载面、风险、变更文件和历史 `tests/e2e/` 推导，并在 `e2e-plan.json` 标明 `obligation_source` 和 `inferred_fields`。检查 `code-review.md` 是否已引用 `e2e_status.status_artifact`；已引用则优先读取同一路径校验状态，不重新解释审查员结论。无界面变更任务项时允许端到端验证义务结论为不适用，但必须由 `e2e-status.json` 记录不适用和 `no_ui_scope` 原因。
 - 条件：e2e.enabled=false
  - 调用 tool: `AskUserQuestion`。
   - 问题：`e2e.enabled=false`：端到端验证已关闭，请确认是否接受此风险。
   - 候选答案：
      - 接受关闭端到端验证（写入 `approval_id` 后继续）
      - 重新开启端到端验证（返回执行 `harness verify e2e-status`）
  - 无批准记录时不得通过；调 `harness approval append --mission <id> --type checkpoint --stage verify --reason "e2e.enabled=false accepted"` 记录用户接受。
</step>

<step id="step-4" n="4" goal="运行测试并收集证据">
 - 调用 cli `harness verify run-tests` `--mission ${mission-id} --layer unit --command ${cmd}`，evidence=required。
 - 调用 cli `harness verify run-tests` `--mission ${mission-id} --layer integration --command ${cmd}`，evidence=required。
 - 所有测试必须通过 `harness verify run-tests` 或 `harness evidence command collect` 收集，禁止绕开收集器直接汇总。若 `project_lint.enabled=true`，在命令证据生成后运行 `harness lint project --mission <id> --command-evidence <path>`；`gate_effect=block` 是项目约束缺口，不得口头改写为通过。
 - 记录每轮测试：运行命令、cwd、started_at、ended_at、exit code、通过/失败数、失败原始错误输出、覆盖率（如工具支持）。
 - 条件：存在测试失败
  - 分析失败原因：实现缺陷 → 记录失败点并继续收集完整证据，调 `harness verify failure-path --kind bug_fix`，按缺陷修复协议路由：缺陷修复 → 执行 → 代码审查 → 验证，不在验证阶段改实现文件；测试本身问题（环境/配置）→ 记为验证障碍，修复后重跑。
 - 条件：e2e.enabled=true
  - 调用 cli `harness verify e2e-status` `--mission ${mission-id}`，evidence=required。
  - 消费 `status`、`obligations`、`runs`、`artifacts`、`missing_capabilities` 和 `decision_gate_reasons`。`e2e-status` 失败 → 工具、报告或产物缺口返回执行或代码审查补齐；真实用户结果不符返回执行修复，受影响验收场景 / 条件不得通过。警告 → 记录缺失能力、不稳定信号（flaky_signals）和跳过测试（skipped_tests）；影响高优先级验收场景 / 条件时按质量控制硬门处理。通过 → 引用 `runs` / `artifacts` 作为端到端验证证据来源，仍需验收追溯证明预期结果与实际结果匹配。
  - 条件：e2e-status.json.status 为 BLOCKED
   - 调用 tool: `AskUserQuestion`。
    - 问题：端到端验证状态为阻塞，请选择处理方式。
    - 候选答案：
       - 接受受限验证（标记为带风险通过，需 `approval_id`）
       - 回代码审查补端到端事实包
       - 回 execute 修复测试环境
   - 发起决策门：引用 `decision_gate_reasons`、受影响义务、缺失产物和下一步选项；端到端验证章节写阻塞，相关验收场景 / 条件的 `acceptance_trace` 写入 `blocked_reason`、`impact` 和 `next_step`。
</step>

<step id="step-5" n="5" goal="对齐验收条件">
 - 逐条比对验收场景 / 条件与测试证据：编号、描述、单元 / 集成证据、端到端场景覆盖、端到端证据和结论。涉及界面的验收场景 / 条件必须有端到端结果证据，不能仅凭单元测试通过、接口响应、模拟响应、数据库检查、内部状态检查或 `e2e-status` 通过来判定。
 - 为每条验收场景 / 条件提取“预期结果”（来自任务契约的 Given / When / Then 或量化指标）和“实际观察结果”（来自一次真实运行、截图、录屏、接口响应、命令行输出、数据状态或文件差异摘要）。
 - 调用 cli `harness contract check-acceptance-trace` `--mission ${mission-id} --artifact harness-runtime/harness/stages/${mission-id}/contracts/verification-report.contract.yaml --upstream harness-runtime/harness/stages/${mission-id}/contracts/execution-brief.contract.yaml`，evidence=required。
 - 校验每条通过的验收场景 / 条件同时引用命令证据和结果证据；界面验收场景 / 条件必须有截图、视频或文档对象模型（DOM）证据；每条证据的 `required_evidence_id` 在执行简报的 `required_evidence` 中有对应标识。失败必须修复，不得降级为带风险通过。
 - 调用 cli `harness verify true-e2e-check` `--mission ${mission-id}`，evidence=required。
 - `true-e2e-check` 校验界面验收场景 / 条件的主要证据类型只能是 `dom`、`dom_snapshot`、`screenshot`、`video`、`trace` 或 `accessibility_snapshot`；接口证据只能标记为准备或交叉检查；模拟证据必须有接口契约或夹具等价性证据。无法自动化真实用户路径时，必须记录决策门或已接受风险，不能静默降级。
 - **等价性证据最小构成**：模拟（mock / 夹具）要被接受，必须同时满足三项——① mock 响应 schema 显式引用上游契约锚点：交互阶段产物 `api_contract_draft.endpoints[]`，或 tech-design 的 `interface_changes` 的 `IF-` ID；② 对该锚点做**字段级 diff 为空**（mock 响应字段集 / 类型与契约定义逐字段一致，无多余 / 缺失 / 类型漂移）；③ **错误语义覆盖**（契约声明的错误码 / 异常分支在 mock 中有对应模拟，非只覆盖 happy path）。三项缺任一，该 mock **不得作为 primary 证据**，只能降级为准备 / 交叉检查证据，对应界面验收场景 / 条件仍需真实浏览器路径的主要结果证据，否则 FAIL。
 - 调用 cli `harness alignment check` `--mission ${mission-id} --stage verify`，evidence=required。
 - 对齐检查校验证据是否回溯到执行简报、交互规格、领域模型和任务契约；程序化失败必须修复或回上游阶段。
 - 验收场景 / 条件标记通过必须同时满足：至少一个命令证据证明检查已运行；至少一个结果证据证明用户可观察结果符合预期；预期结果与实际结果语义逐项匹配。按交付类型收集结果证据：界面 / 浏览器、接口、命令行 / 脚本、数据 / 后台任务、文档 / 配置。没有自动化测试覆盖的验收场景 / 条件必须说明手动验证步骤和结果；未能验证的验收场景 / 条件必须明确标注原因。每条验收结论写入现有 `acceptance_trace` 字段；通过项引用至少一个命令证据和一个结果证据；阻塞项写入 `blocked_reason`、`impact` 和 `next_step`。
 - 条件：验收场景 / 条件证据不足或证据缺口影响交付判断
  - 读取 `.harness/common/protocols/quality-control/PROTOCOL.md`，将缺口分类为硬门、软门或观察项；硬门不得继续。
 - 条件：`code-review.md` 存在未修复或未接受风险的高严重级别发现
  - 调用 tool: `AskUserQuestion`。
   - 问题：代码审查存在未关闭的高严重级别发现，请选择处理方式。
   - 候选答案：
      - 回接收审查反馈阶段（默认）
      - 接受风险（需 `approval_id` 记录）
      - 回执行阶段修复
  - 结论不得为通过；按用户选择走对应 failure path；无用户决策时默认路由到 receiving_review。
</step>

<step id="step-6" n="6" goal="生成 verification-report.md">
 - 使用 `harness-runtime/templates/verification-report.md` 模板结构，按验证证据契约（Verification Evidence Contract）填充。若 `contracts/verification-report.contract.yaml` 不存在，调用 `harness contract init --mission <id> --stage verify --template verification-report --json` 初始化；`control_contract.type=evidence_contract`、`subtype=verification_evidence`，验证证据契约包含 `command_evidence`、`result_evidence` 和 `acceptance_trace`。系统操作覆盖写入 Markdown 的“系统操作覆盖与自洽矩阵”；质量与运行约束通过结果证据和验收追溯表达，不再单独维护 NFR 追溯字段。
 - `result_evidence[]` 记录预期结果、实际结果、复现方式、产物和结果；`command_evidence[].artifact` 指向证据仓库 JSON；`command_evidence[].required_evidence_id` 和 `result_evidence[].required_evidence_id` 引用拆解阶段执行简报 `tasks[].required_evidence[].id`，不得自创。
 - 填充章节：验证依据目录、验证目标、验证模型、系统操作覆盖与自洽矩阵、验证方法、验证结果（验收场景 / 条件对齐表、测试统计、预期 / 实际对照）、端到端验证结果（引用 `e2e-status.json`、端到端统计、场景与验收条件对齐、网页报告、追踪 / 视频 / 截图、不适用原因、阻塞决策门记录）、风险与质量约束验证、未覆盖范围、遗留问题、验证评价摘要。`verification-report.md` 的“控制契约”段只保留 `Contract:` 引用，禁止追加围栏式 YAML 契约。
 - 写入 `harness-runtime/harness/stages/<mission-id>/verification-report.md`；将验证证据契约字段、`execution_result`、`role_verdicts` 经 `harness-cli` 写入外部契约。
 - 调用 cli `harness verify detect-contradictions` `--mission ${mission-id} --artifact harness-runtime/harness/stages/${mission-id}/contracts/verification-report.contract.yaml`，evidence=required。
 - 检测 `acceptance_trace.conclusion` 与命令、结果、端到端验证和角色结论之间的结构矛盾，例如 `command_evidence.result=fail` 但验收场景 / 条件写通过；失败时必须修复，不自动降级。
</step>

<step id="step-7" n="7" goal="验证结论与后续">
 - 调用 cli `harness verify compute-conclusion` `--mission ${mission-id}`，evidence=required。
 - 返回通过、失败、阻塞、带风险通过四态结论和 `failure_path`。
 - 分支：结论
  - 情况：通过
   - 可以进入阶段门；阶段门通过后由泳道动作的图操作推进到交付泳道。
  - 情况：带风险通过
   - 调用 tool: `AskUserQuestion`。
    - 问题：验证结论为带风险通过，存在未关闭的残留风险，请确认是否接受。
    - 候选答案：
       - 接受残留风险（写入 `approval_id`）
       - 不接受，返回对应失败路径修复
   - 无批准记录时，`compute-conclusion` 不能返回带风险通过；调 `harness approval append --type risk --stage verify` 记录用户接受。
  - 情况：失败
   - 调 `harness verify failure-path --kind <bug_fix|execute>`；列出需修复的验收场景 / 条件清单；返回执行技能修复后重新运行验证；不在验证阶段改实现文件。
  - 情况：阻塞
   - 调用 tool: `AskUserQuestion`。
    - 问题：验证结论为阻塞，请选择处理方式。
    - 候选答案：
       - 接受当前范围风险（需 `approval_id`）
       - 补环境后重跑
       - 缩小交付范围（回 execute 更新任务项）
   - 调 `harness verify failure-path --kind decision_gate`；发起决策门，让用户决定是否接受当前验证范围。
</step>

<step id="step-8" n="8" goal="产物门自检">
 - 进入本步骤前，若 Step 9 的 Agent Eval 条件命中，必须先完成 Agent Eval 并把结论写回 verification-report.md 与 contract；否则 Gate 不得通过。
 - 验证 `verification-report.md` 包含最小必要结构：验证目标 / 验证方法 / 验证结果 / 遗留问题；前部含 `Contract:` 引用且不含围栏式 YAML 契约、`## evidence_contract`、`## execution_result` 或 `## role_verdicts`。
 - 验证外部契约包含验证证据契约，所有通过的验收场景 / 条件同时引用命令证据和结果证据；阻塞项都含原因、影响和下一步。端到端验证结果章节已按实际填写。
 - 条件：`role_verdicts` 中验证有效性审查员最新结论仍为 HOLD
  - 产物门不得通过。回步骤 2 的 HOLD 闭环分支（按缺口失败路径回流 → 修复 → 重新 dispatch 验证有效性审查员重审，无轮次放行、每轮等同严格度）；只有最新 `role_verdict` 在等同严格度下转为 PASS，或卡死后已升级为决策门、用户显式拥有残留风险并有 `approval_id` 批准记录时，才允许继续 gate 自检。
 - 调用 cli `harness verify gate run` `--mission ${mission-id}`，evidence=required。
 - `gate run` 内部聚合 `contract check-acceptance-trace`、`verify true-e2e-check`、`verify prototype-alignment-check`、`verify detect-contradictions` 和通用阶段门，输出类型化失败检查（`typed failed_checks`）；程序化失败必须修复后再进入交付。
 - 条件：本 mission 有 interaction 原型产物（`prototype.delivery_mode=interactive_prototype` 且存在 behavior-graph）
  - 聚合子项 `harness verify prototype-alignment-check` 与 `true-e2e-check` 并列：对 behavior-graph 里每个 `e2e_obligation=true` 的 edge，要求其 `testid` 被某条通过的 e2e 断言覆盖（covered_testids 来源 = verification-report 的 `result_evidence` 记录的 testid）。未覆盖 FAIL `PROTOTYPE_E2E_EDGE_NOT_ASSERTED`（阻断门）；testid 占位 / 缺失 WARN `E2E_OBLIGATION_EDGE_NO_TESTID`。合法出口是 `prototype_coverage_exemptions:[{id,reason}]`（理由缺失 FAIL `PROTOTYPE_EXEMPTION_NO_REASON`）。`PROTOTYPE_E2E_EDGE_NOT_ASSERTED` 必须修复（补 e2e 断言并在 `result_evidence` 记录命中 testid）或经决策门登记豁免 + 理由后才能进入交付，不得口头改写为通过。非 UI / 未跑 interaction 时本子项自动跳过。
 - 条件：gate status != PASS
  - 按 failed_checks 修复验证报告、证据 contract 或返回对应 failure path；不得完成阶段。
 - 调用 cli `harness mission stage complete` `--mission ${mission-id} --stage verify --json`，evidence=required。
 - 条件：结构不完整
  - 自行补充缺失部分，不要跳过。
</step>

<step id="step-9" n="9" goal="条件：执行 agent-eval 技能">
 - 条件：agent_engineering.require_agent_eval=true
  - 调用 cli `harness verify agent-eval-status` `--mission ${mission-id}`，evidence=required。
  - 参考 `docs/methodologies/agent-capability-engineering.md` §7。确认 `tech-design.md` 的 `## Agent 实现` 声明的智能体组件均已实现，且执行简报中对应的智能体任务项全部完成。
  - 条件：`tech-design.md` 存在智能体实现规格且智能体实现完成
   - 调用 skill `agent-eval` `mission=${mission-id}`。
   - 分支：eval 结论
    - 情况：全部通过
     - `verification-report.md` 的智能体行为验证段填写通过，引用评估报告路径。
    - 情况：有能力未达标（高严重性）
     - `verification-report.md` 记录智能体评估未通过和失败列表；调 `harness verify failure-path --kind execute` 返回执行修复后重新运行验证。
  - 条件：agent_engineering.enabled=true 但 tech-design.md 缺少 Agent 实现规格
   - `verification-report.md` 记录：缺少 `tech-design.md` 的 `## Agent 实现`，智能体评估阻塞；返回技术分析补齐实现规格。
</step>

</steps>

<failure_paths>

| 失败类型 | 触发条件 | 处理方式 |
|---|---|---|
| `bug-fix` | `compute-conclusion` 返回失败，`acceptance_trace` 有 `conclusion=fail` 条目（实现缺陷） | 调 `harness verify failure-path --kind bug_fix`；按缺陷修复协议走复现证据 → 根因 → 修复 → 回归证据；完成后重走执行 → 代码审查 → 验证。 |
| `blocked-execute-failure` | `compute-scope` 的 `execute_failure_ref` 非空（执行阶段已有失败证据） | 调 `harness verify failure-path --kind execute`；验证阶段直接进入阻塞结论，不重跑双证据校验；触发复盘和缺陷修复；`execution-result.contract.yaml.failure_state` 必须在 `acceptance_trace.execute_failure_ref` 中显式引用。 |
| `decision-gate` | `compute-conclusion` 返回阻塞，`decision_gate_reasons` 非空（测试环境受阻） | 调 `harness verify failure-path --kind decision_gate`；引用 `decision_gate_reasons`、受影响义务和缺失产物；调 `harness approval append --type risk --stage verify` 记录用户决策，无批准记录不得继续。 |
| `receiving-review` | 代码审查高严重级别发现未修复且未接受风险 | 调 `harness verify failure-path --kind receiving_review`；路由回接收审查反馈，直到高严重级别发现全部关闭或批准后再回验证。 |
| `execute-evidence-missing` | `check-acceptance-trace` 强校验失败（`VERIFY_EVIDENCE_ID_NOT_IN_UPSTREAM`）且 `execute_failure_ref` 为空 | 调 `harness verify failure-path --kind execute`；路由回执行补齐缺失证据，不允许验证阶段自行降级为带风险通过；执行补完后重回验证并重跑步骤 3-7。 |

</failure_paths>

阶段流转：

- 决定来源：任务切片（Mission Slice）中的 `control_plane.stage`。
- 典型下一步：
  - `delivery`：验证结论为通过，或带风险通过且已有批准记录。
- 执行方式：`harness gate advance`

</workflow>
