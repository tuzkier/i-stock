# 拆解工作流

> **方法论参考**:`.harness/docs/methodology-reference.md` §6(OpenSpec propose 工作流;Vertical Slicing - 每个任务项是可独立交付的价值纵切片)

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用(默认带 `--json`、消费 typed payload;详见 `.harness/common/skills/harness-cli/SKILL.md`)。

<workflow stage="breakdown" version="2">

<goal>
  将已成立的产品定义、方案和技术设计转化为一次受控迭代的执行授权。执行简报(execution-brief.md)必须说明本轮增量交付什么、覆盖哪些 `SUC-xx-OP-xx` 系统操作、优先消除哪些风险、授权哪些变更集、哪些条件必须停止或回流,并在首次写盘时为每个父任务(Parent task)产出内嵌 `atomic_task_queue`。父任务是交付切片 / 任务节点(TASK node)边界;原子任务(Atomic Task)是执行阶段(execute)的实际执行单位。简单父任务也必须至少含 1 个原子任务;不得先写父任务骨架再把原子任务队列(Atomic Task Queue)当作常规补丁追加。
</goal>

<role>
  你是迭代工作授权设计者。你从上游产品定义包、方案和技术设计中提炼执行者必须知道的一切,确认输入足以支撑执行授权,再把高层设计分解为有风险顺序、变更边界和验证义务的任务项。任务项拆得好,执行者照着干就不会出错;拆得差,再好的 TDD 循环也救不了方向错误。你不替上游补产品行为、方案决策或技术设计。
</role>

<stage_capability>

拆解阶段对应 RUP 项目管理中的迭代计划 / 工作授权，以及配置与变更管理中的变更集边界。它的核心能力不是把设计拆成清单，而是回答“AI 可以在什么边界内独立执行、如何证明、何时停止”。

| 能力 | 判断问题 | 产物要求 |
|---|---|---|
| 输入合格性判断 | 产品定义包、方案、技术设计、交互产物和项目上下文是否足以推出父任务边界、系统操作覆盖、验证义务和停止条件。 | 在 `execution-brief.md` 写清来源、执行义务、是否足够和处理动作；上游不足时回流，不在拆解阶段补设计。 |
| 执行义务映射判断 | 上游系统责任、`SUC-xx-FLOW-xx` 流步骤、`SUC-xx-OP-xx` 系统操作、验收场景 / 条件、质量与运行约束、领域规则、方案决策、技术设计 ID 和风险如何进入执行任务。 | 建立义务映射和系统操作覆盖检查；任何不能绑定上游义务或证据的任务必须删除、合并或回流。 |
| 迭代授权判断 | 本轮交付什么增量、先处理什么风险、授权哪些变更集、哪些内容不做或延后。 | 写出增量目标、风险焦点、授权变更集、非目标、延后项和停止 / 回流条件。 |
| 父任务切分判断 | 父任务是否按用户可观察结果、事务边界、风险验证目标、状态迁移、权限规则或不可拆变更集纵切。 | 父任务标题和内容必须体现交付结果、风险目标和变更边界；不得按文件层或技术层水平拆分。 |
| 原子任务队列判断 | 每个父任务是否已经包含可执行的父任务本地原子任务队列。 | 首次写盘时每个父任务必须有 `atomic_task_queue.status=ready` 和同 ID 原子任务详情；不得等待后续补计划。 |
| 证据与停止条件判断 | 每个原子任务是否有输入、输出、读写范围、样板、验证命令、证据路径和停止条件。 | 执行者只读执行简报即可知道做什么、怎么验证、哪些信号必须停止并回流。 |

</stage_capability>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `brief-contract-via-cli` | execution-brief.contract.yaml 不得被 agent 直接 Write/Edit,必须经 harness contract fill/patch/record-review；`add-verdict` 仅用于导入既有 verdict manifest | hook=breakdown-check-contract-via-cli |
| `brief-not-fenced` | execution-brief.md 不得内嵌 fenced YAML action_contract / execution_result / role_verdicts 段 | hook=harness-lint |
| `atomic-queue-first-write` | execution-brief.md 首次写盘时每个父任务(Parent task)必须已含 ready 状态的 `atomic_task_queue` + 原子任务详情(Atomic Task detail),禁止先写父任务骨架再补 | hook=breakdown-check-first-write-completeness |
| `parallel-barrier` | delivery-slicer 与 test-planning-expert 并行 barrier 必须双双 DONE 才能集成 | hook=breakdown-check-barrier-complete |
| `reviewer-readonly` | execution-plan-effectiveness-reviewer 必须在 readonly subagent 中调用 | registry=subagents/execution-plan-effectiveness-reviewer[readonly=true] |

</invariants>

<entry>
  - design 阶段已完成(solution / tech-design + 各 contract PASS)
  - skill-router 已判定本消息属 breakdown 阶段
  - 上游设计足以支撑执行授权:`SUC-xx-OP-xx` 系统操作、验收场景 / 条件、质量与运行约束、选定方案、模块责任、接口 / 数据 / 状态变化、风险验证方式和实施边界均可被拆成任务
</entry>

<exit>
  - `input-fit-for-authorization`: 已确认上游输入足以拆解;若不足,已回流到产品定义、方案或技术分析,而不是在 breakdown 内补造设计
  - `iteration-authorization`: execution-brief.md 明确本轮增量目标、风险焦点、授权变更集、非目标、延后项和停止 / 回流条件
  - `brief-written`: execution-brief.md 写入 breakdown stage worktree,每个父任务(Parent task)含 `atomic_task_queue.status=ready`
  - `slice-hinge-review-pass`: step-1 切片枢纽审查闸经 execution-plan-effectiveness-reviewer 在等同严格度下对切片维度 PASS(或已澄清回填 / Decision Gate approval)后才合并测试义务;未 PASS 不得合并发布完整拆解规划包
  - `contract-filled`: execution-brief.contract.yaml 已填充且 harness contract check PASS
  - `reviewer-pass`: execution-plan-effectiveness-reviewer PASS 或用户降级 approval 已记录
  - `spec-coverage`: spec.enabled=true 时 harness execution-brief check-coverage --spec-mode strict PASS
  - `gate-pass`: harness execution-brief gate run 返回 quality_check + artifact_gate 双 PASS
</exit>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `delivery-slicer` | spawn | harness-runtime/harness/artifacts/${mission-id}/breakdown/execution-brief.md | `.harness/common/agents/delivery-slicer.md` |
| `test-planning-expert` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/test-planning-expert.md` |
| `execution-plan-effectiveness-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/execution-plan-effectiveness-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `product/product-definition.md` | true | Memory |
| `product/use-case-model.md` | true | Memory |
| `product/acceptance-scenarios.md` | true | Evidence |
| `product/product-domain-model.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `solution.md` | true | Memory |
| `tech-design.md` | true | Memory |
| `interaction.md` | conditional: interaction lane 已完成 | Memory |
| `interaction-spec/use-case-realization.md` | conditional: interaction lane 已完成且涉及界面或用户路径 | 用例到交互实现基线 |
| `interaction-spec/surface-model.md` | conditional: interaction lane 已完成且涉及界面或用户路径 | 界面边界、信息架构和领域到界面映射 |
| `interaction-spec/interaction-contract.md` | conditional: interaction lane 已完成且涉及界面或用户路径 | 路径、状态、交互和端到端验证要求 |
| `project-context.md` | conditional: brownfield | Context |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `execution-brief-md` | `harness-runtime/harness/artifacts/${mission-id}/breakdown/execution-brief.md` | markdown | Memory |
| `execution-brief-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/execution-brief.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化">
 - 调用 `harness mission stage start breakdown --json` → `harness trace log-init`,建立本阶段 trace。
 - 读取上游文档:`harness-runtime/harness/missions/<mission-id>/mission-contract.md`、`harness-runtime/harness/artifacts/<mission-id>/product/product-definition.md`、`harness-runtime/harness/artifacts/<mission-id>/product/use-case-model.md`、`harness-runtime/harness/artifacts/<mission-id>/product/acceptance-scenarios.md`、`harness-runtime/harness/artifacts/<mission-id>/product/product-domain-model.md`、`harness-runtime/harness/artifacts/<mission-id>/product/product-evidence.md`、`harness-runtime/harness/artifacts/<mission-id>/solution/solution.md`、`harness-runtime/harness/artifacts/<mission-id>/technical-analysis/tech-design.md`、`harness-runtime/harness/artifacts/<mission-id>/interaction/interaction.md` 与 `interaction-spec/use-case-realization.md`、`interaction-spec/surface-model.md`、`interaction-spec/interaction-contract.md`(如存在),以及 `harness-runtime/harness/artifacts/<mission-id>/interaction/frontend-changeset.md` 与 `contracts/prototype-as-frontend.contract.yaml`(如存在,前端工程路线 frontend_engineering)。拆分必须覆盖 `SUC-xx-OP-xx` 系统操作，以及领域驱动设计(DDD)模型中的领域命令(domain command)、不变量(invariant)、状态迁移(state transition)、权限规则(permission rule)和异常 / 补偿场景(exception / compensation case);UI / 用户旅程任务必须以交互规格中的用例实现、界面模型和交互合同生成执行边界,或以前端工程产物中的定位器义务(locator obligations)生成执行边界,不得只按页面或文件机械拆分。
 - **输入合格性判断**:在拆任务前先判断上游是否足以支撑执行授权:
   - 产品定义包必须能说明本轮要覆盖的 `SUC-xx-OP-xx` 系统操作、验收场景 / 条件、质量与运行约束、范围内 / 范围外和用户可观察结果。
   - solution 必须能说明选定路线、禁止路线、关键决策依据和高优先级风险处理方式。
   - tech-design 必须能说明每个 `SUC-xx-OP-xx` 的技术承载、模块责任、接口契约、数据 / 状态变化、依赖影响、验证策略、实施边界和停止条件。
   - 交互 / 前端工程产物(interaction / frontend engineering,如适用)必须能说明作用面(surface)、用户路径、状态、端到端(E2E)义务或定位器(locator)义务。
   - 若缺口属于产品行为、方案路线、模块 / 接口 / 数据设计、风险验证方式或能力边界,不得在拆解阶段(breakdown)内补设计;返回对应上游阶段或发起决策门禁(Decision Gate)。只有执行计划表达不清、任务粒度不当、证据要求不具体这类拆解阶段自身缺口,才在本阶段修复。
 - **输入合格性判定方法**:
   - 对每类输入建立 `来源 -> 执行义务 -> 是否足够 -> 处理动作` 的四列判断。`来源` 必须指向上游文档章节、ID 或稳定段落;不能只写"已确认"。
   - `是否足够` 只允许:`fit`、`return_to_prd`、`return_to_solution`、`return_to_tech_design`、`return_to_interaction`、`return_to_agent_capability_design`、`needs_decision`。
   - 判为 `fit` 时,必须能从上游直接推出至少一个父任务(Parent task)边界、一个验证义务和一个停止条件。
   - 判为 return / decision 时,必须写明缺少的上游结论、为什么 breakdown 无权补齐、继续拆解会导致什么执行风险。
 - **前端工程路线(frontend_engineering)的作用面标签约束**:如果 `harness config snapshot` 的 `prototype.delivery_mode=frontend_engineering` 且上游 `contracts/prototype-as-frontend.contract.yaml` 存在:
   - 前端相关任务的作用面(surface)标签**只允许**:`frontend_integration`(MSW → 真 API 切换 + 联调)、`frontend_test_hardening`(写 e2e + 单元 / 组件测试)、`frontend_bug_fix`(修联调暴露的 bug)。
   - 不允许在执行阶段(execute)产出 `frontend_ui` 标签的任务;这意味着新前端 UI 需求应该回交互阶段(interaction stage)处理。若上游产物提示存在此类需求,停下来发起决策门禁(Decision Gate)。
   - 每个 `frontend_test_hardening` 任务必须引用 contract 的 `e2e_locator_obligations[]` 中至少一个 `path_id` 作为实现目标。
 - 调用 `harness context check --json`;PASS 则读取 `project-context.md`;FAIL 时按 `project-context` 规则处理,并在拆解证据(breakdown evidence)中记录 `inputs_missing.project_context=true`,不得静默继续。
 - 调用 `harness config snapshot --json`,获取 `spec.enabled`、执行模型策略摘要和 lane action 注册表;不得直接读取 `harness-runtime/config/harness.yaml` 或 `model-routing.yaml`。
 - 条件:spec.enabled=true
  - 从 `harness config snapshot` 读取 breakdown 附加约束摘要;调用 `harness spec diff list --mission <mission-id> --json` 列出全部差量规格 Scenario 及其覆盖状态,作为后续 Step 3c 全局覆盖检查的输入。
 - 从 `harness frame current --mission <mission-id> --json` + `harness config snapshot --json` 取得拆解阶段(breakdown)角色策略(role policy);默认执行子智能体(Agent)为 `delivery-slicer` / `test-planning-expert`,审查子智能体为 `execution-plan-effectiveness-reviewer`。
 - 从 tech-design.contract.yaml 派生 `agent_engineering` 触发判定,供 Step 9 条件触发消费。
 - 使用当前 Mission Slice 和 lane action 快照;breakdown 的任务项必须能映射为 TASK node 候选,不能只停留在 Markdown 列表。
</step>

<step id="step-1" n="1" goal="专业角色调度">
 - 调度子 Agent `delivery-slicer`(可写,写 execution-brief.md 草稿与 `atomic_task_queue`)+ `test-planning-expert`(只读,返回任务级测试义务约束 / 矩阵)。两者可以并行读取上游材料,但语义顺序必须明确:`delivery-slicer` 先形成任务候选图(task candidate map,含父任务 / 原子任务 / 作用面 / 验收场景追溯(可含 AC 锚点)/ 风险 / 授权路径),`test-planning-expert` 的最终测试义务必须绑定到这份候选切片上;若只拿到空图,可以先建立验收场景 / 条件、风险和作用面义务索引,但不能产出最终泛化测试矩阵。
 通过 `@delivery-slicer` native delegation调用 `delivery-slicer` subagent（Cursor auto-routes 到对应 agent registry 项）
 通过 `@test-planning-expert` native delegation调用 `test-planning-expert` subagent（Cursor auto-routes 到对应 agent registry 项）
 - delivery-slicer Task Envelope:产品定义包、solution、tech-design、三份 interaction-spec(如存在)、差量规格(delta specs)、项目上下文(project-context)、**实现代码库源码根(供样板间检索)** 和 `harness knowledge resolve --stage breakdown` 返回的 `engineering/patterns` 索引;输出路径 `execution-brief.md`(草稿,每个父任务内嵌 `atomic_task_queue` + 测试 / 端到端义务占位块);返回任务候选图(task_id、作用面、验收场景 / 条件 / Scenario 追溯、风险、授权路径、风险消减、变更集边界)。**每个涉及代码变更的原子任务的代码模式参考,必须由 delivery-slicer 在实现代码库里真实检索得到(按其角色包「代码模式参考(样板间)检索规程」),`Reference path` 指向真实源码文件;确无同类才写 `no_match` + 搜索范围;禁止用 `artifacts/**` 阶段产物或 `IF-/MOD-/DATA-/VS-` 技术设计 ID 冒充样板。**
 - test-planning-expert Task Envelope:同一组上游材料 + delivery-slicer 任务候选图;返回任务级 / 原子级测试义务矩阵(不写盘)。
 - **切片枢纽审查闸(先于义务合并)**——按 `core.md`「step 级枢纽审查」执行:delivery-slicer 的任务候选图 / 切片是枢纽工件,test-planning-expert 的测试义务将绑定其上、后续步骤也基于它派生;若切片本身有缺陷(父任务边界错、作用面错、漏 AC 追溯、授权路径越界)就先合并义务,缺陷会被义务矩阵和后续步骤多跳放大,到 step-6 末尾审查才发现则切片与测试义务两侧都要返工。等两个子 Agent 都返回后、执行义务合并(下一条)之前,先对切片维度过收窄审查:
   通过 `@execution-plan-effectiveness-reviewer` native delegation调用 `execution-plan-effectiveness-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
   - 任务信封(收窄实例化):审查对象 = delivery-slicer 写出的 execution-brief.md 草稿中的**父任务切片维度**(父任务边界、作用面、验收场景 / 条件追溯、授权路径、停止条件、变更集边界、原子任务划分)+ 返回的任务候选图;直接上游 = 产品定义包、solution、tech-design、interaction-spec(如存在)、差量规格、`materials/` 原始材料与已确认澄清、project-context;只读约束;审查清单收窄到切片是否按用户可观察结果 / 事务边界 / 风险验证目标 / 状态迁移 / 权限规则纵切(非按文件层 / 技术层水平拆)、每个父任务能否追溯到 `SUC-xx-OP-xx` 与验收锚点、授权路径是否越界。**本步只审切片,不审测试义务**(测试义务由 step-6 末尾全量审查覆盖)。结论经 `harness contract record-review --artifact contracts/execution-brief.contract.yaml --role execution-plan-effectiveness-reviewer --verdict <PASS|HOLD|BLOCKED> --reviewed-obligation HINGE-slice-candidate-map --review-basis <.../execution-brief.md> --subagent-id <id> --model <model> --summary <...> --json` 写入 `role_verdicts`(hinge-scoped `--reviewed-obligation` 必传,不消耗 step-6 reviewer-loop 轮次,不冒充末尾 reviewer-pass,见 `core.md`「step 级枢纽审查」记录约束)。
   - 循环:无轮次放行;退出条件:execution-plan-effectiveness-reviewer 在等同严格度下对切片维度返回 PASS。
     - HOLD / BLOCKED:切片自身缺陷 → 重新 dispatch `delivery-slicer` 重切后原地重审(切片变更后,若已绑定的测试义务受影响,test-planning-expert 须按新切片重新绑定);信息缺失需上游澄清(`gap_root=clarification`,如系统责任 / 边界须用户定义)→ 不消耗轮次,走澄清后重导。
     - 卡死:不得降级通过,按 `core.md`「严格审查不变量」重新归因;需用户拍板时 AskUserQuestion,候选不含降级通过(继续修 / 回技术设计或设计 / 升级 BLOCKED),残留风险走 Decision Gate `harness approval`。
   - 切片枢纽审查 PASS 后才能进入下一条的义务合并;未 PASS 不得合并发布完整拆解规划包。
 - 等待两个子 Agent 返回后,由主流程按 `parent_task_id` / `atomic_task_id` / 作用面 / AC 追溯把 `test-planning-expert` 的义务矩阵合并到 `delivery-slicer` 写出的 execution-brief.md(替换占位块),形成内存中完整的拆解规划包(breakdown planning packet);此时不得发布只含父任务、仅占位义务或未合并测试义务的中间 execution-brief,也不得把原子任务队列(Atomic Task Queue)推迟给常规后置补丁。
 - 外部 `contracts/execution-brief.contract.yaml` 后续写盘时必须写入每个执行角色的 `execution_result`(含 delivery-slicer 与 test-planning-expert 两条),不得只保留其中一个。
</step>

<step id="step-2" n="2" goal="从上游文档提炼执行上下文">
 - 从任务契约提取:验收条件、约束、交付要求。
 - 从产品定义包提取:每条系统责任、`SUC-xx-FLOW-xx` 流步骤、`SUC-xx-OP-xx` 系统操作、验收场景 / 条件和质量与运行约束的核心内容(去掉分析过程,只保留结论)。
 - 从 solution 提取:已确定的方案选择(去掉被否决的方案)。
 - 从 solution.md 的 Solution 指导契约提取 decisions、forbidden_paths、risks,作为任务项设计约束。
 - 从 tech-design 提取:系统操作到技术设计映射、模块划分和职责、接口定义、实现策略和顺序、对现有系统的影响点。
 - 从 tech-design.md 的技术指导契约提取 MOD / IF / DATA / VS ID,作为任务项 `traces_to` 的技术约束来源。
 - 条件:本 mission 有原型产物(interaction lane 已完成且产出 `interaction-spec/behavior-graph.yaml`)
  - 从 behavior-graph.yaml(原型契约 SSOT)提取 page_state(稳定 ID `PS-<surf>-<state>`)与 surface(`SURF-xxx`),从 surface-model.md 提取每个 SURF 的界面边界动作(create / modify / extend / retire + baseline),作为前端 / 交互任务项 `traces_to` 与变更集边界的原型层来源。前端 / 交互任务的 `traces_to` 应指向对应 `PS-`(page_state),并把 surface 的 create / modify / extend / retire 界面边界落进任务变更集与 `authorized_paths`;不得对原型决策静默漂移或自由重设计界面。确不承载某 `PS-` / `SURF-` 时,必须经决策门禁显式改写并在契约 `prototype_coverage_exemptions: [{id, reason}]` 登记理由。
 - 调用 `harness knowledge resolve --stage breakdown --json`,读取返回的 project-knowledge 路径;重点提取 engineering/task-splitting、engineering/patterns、engineering/testing 中的本项目样板间和拆分约定。
 - 从 project-context / project-knowledge/context 提取:编码规范要点、技术选择限制、已知的坑。
</step>

<step id="step-2b" n="2b" goal="RUP 拆解方法:从设计义务到执行授权">
 - 拆解方法、父任务/原子任务的切分/合并条件、命名约定和验证绑定规则详见 `delivery-slicer` 角色包方法步骤和 `execution-brief.md` 模板填写约定。workflow 本 step 只补充以下 workflow 级边界约束:
 - 建立 obligation map 后,任何无法绑定到上游义务或证据的任务不得保留,必须删除、合并或回流上游阶段。
 - 排序方法:先做依赖拓扑排序,再按风险前置调整顺序。会影响后续任务成立的接口兼容、数据迁移、权限边界、外部依赖、智能体(Agent)约束、关键状态机和端到端(E2E)用户路径验证,应排在依赖其结论的实现任务之前。
</step>

<step id="step-3a" n="3a" goal="父任务(Parent task)分解 + 顺序 + 依赖">
 - 基于 Step 2b 的拆解结果,确认父任务候选项的顺序与依赖。父任务是交付切片 / 任务节点(TASK node)边界,也是本轮迭代的工作授权单(work order)边界。
 - workflow 级边界约束:优先安排会影响后续实现成立的高风险 / 高不确定性任务,例如接口兼容、数据迁移、权限边界、外部依赖、智能体(Agent)约束、端到端(E2E)用户路径和关键状态机。
 - 本子步骤只产出父任务骨架(目标 / 完成边界 / 顺序 / 依赖);原子任务队列(Atomic Task Queue)在 Step 3b 同步成形,不得把 3a 的父任务骨架直接写盘。
</step>

<step id="step-3b" n="3b" goal="每个父任务（Parent task）的 atomic_task_queue 12 字段">
 - 为每个父任务设计内嵌原子任务队列（Atomic Task Queue）。父任务和原子任务（Atomic Tasks）必须一起成形；不得先确认父任务再启动常规二次拆解。
 - 原子任务队列 12 字段的填写规则、分解原则和完成清单详见 `execution-brief.md` 模板填写约定和 `delivery-slicer` 角色包。workflow 本 step 只补充以下边界约束：
   - 每个父任务必须包含目标 / 本轮增量价值 / 风险处理目标 / 变更集边界 / 完成边界 / 实现约束 / 测试要求 / 相关文件 / 规格引用（仅 spec.enabled=true）/ 必需证据 / 测试义务 / 停止条件 / guide 引用 / `atomic_task_queue`（至少 1 个原子任务）。
   - 规格引用格式：`<capability>/spec.md#<Requirement>/<Scenario>`。guide 引用至少一个 DEC-/MOD-/IF-/DATA-/VS- ID。本 mission 有原型产物时，前端 / 交互父任务的 `traces_to` 还应包含对应 `PS-`（page_state，来自 behavior-graph.yaml）；承载 surface 的任务把对应 `SURF-` 界面边界写进变更集与 `authorized_paths`。
   - **默认交互原型路线（interactive_prototype）的 e2e 断言义务**：本 mission 有 behavior-graph.yaml 且任务含 UI 时，该任务的 `test_obligation` / e2e 义务必须显式声明它要断言的 behavior-graph `edge.testid`（`e2e_obligation=true` 的 edge）与关键 `page_state.state`（状态结局：loading/empty/error/readable… 及其 anchor_root）；声明的 testid 须命中原型 data-testid，供验证阶段（verify）的证据回填断言锚点。这与前端工程路线（frontend_engineering）每个 `frontend_test_hardening` 任务引用 `e2e_locator_obligations[].path_id`（见 Step 0）对称。
</step>

<step id="step-3c" n="3c" goal="spec 全局覆盖检查">
 - 条件:spec.enabled=true
  - 全局覆盖检查:Step 0 `harness spec diff list` 列出的每一份差量规格文件里每个 ADDED/MODIFIED Scenario,都必须至少被一个任务项的「规格引用」覆盖。机器判定走 `harness execution-brief check-coverage --mission <mission-id> --spec-mode strict --json`。
  - 未被覆盖的 Scenario → 补任务项或合并到既有任务项;不得遗漏。
  - Hard gate `spec-scenario-coverage`:不允许「这个 Scenario 太小所以不单独写任务项」式的合理化。Scenario 是行为契约单位,要么被测试覆盖,要么从差量规格里拿掉(回产品定义阶段修订)。
</step>

<step id="step-4" n="4" goal="准备产物包结构">
 - 使用 `harness-runtime/templates/execution-brief.md` 模板结构准备待写入内容,但本步骤只组装内存结构,不写盘。
 - 写入模板章节时必须落实模板内的填写约定:输入合格性要有来源和处理动作,迭代授权要有增量目标 / 风险焦点 / 变更边界,RUP 拆解约定要有义务映射(obligation map)、父任务切分理由、原子任务切分理由和风险排序说明。不得只新增章节名或用"已确认 / 相关代码 / 执行相关测试"这类占位表达替代方法。
 - 根据 Step 3 的粒度策略准备以下章节:外部控制契约(初始化并填充 `contracts/execution-brief.contract.yaml`,type 必须为 action_contract,每个任务项记录 id / traces_to / authorized_paths / prohibited_paths / required_evidence / test_obligation / stop_if / dependencies)/ TL;DR / 任务目标 / 输入合格性判断 / 迭代授权摘要 / 硬性约束 / 接口与数据变更速查 / 风险优先级与任务顺序 / 原子任务队列策略(Atomic Task Queue)/ 已知风险与注意事项 / 执行单元(Execution Units,父任务 + 内嵌 atomic_task_queue)/ 完成定义(Definition of Done)/ 验收条件速查 / 上游文档引用。execution-brief.md 的"控制契约"段只保留 `Contract: contracts/execution-brief.contract.yaml` 引用和 Authority 说明,禁止追加 fenced YAML contract。
 - 父任务(Parent task)不得承载文件级行动、代码模式参考、fixture 细节、执行期验证命令(execute-time validation commands)或原子任务顺序;调度元数据只进入同一父任务内的 `atomic_task_queue.execution_units[]`,执行说明进入同 ID 的原子任务详情(Atomic Task detail)块。不得只输出表格或只输出 atomic_task_ids,也不得在 detail 块里重复维护第二份 YAML 调度元数据。
 - 不得在拆解工作流(breakdown workflow)内手工把当前任务切片(Mission Slice)标记完成或进入执行阶段(execute);`execution-brief.md` 是产物名,不作为调度阶段键(stage key)。阶段完成、工作图(Work Graph)推进和下一张任务切片只能由阶段门禁(Stage Gate)后的 `harness gate advance` 写入。
</step>

<step id="step-5" n="5" goal="任务节点(TASK node)输出计划">
 - 读取 `lane_action.output_artifact`,确认 execution-brief 是本动作(action)的阶段产物(stage artifact)。
 - 每个可独立执行的任务项必须具备任务节点(TASK node)候选信息:稳定任务 ID、标题(title)、泳道(lane)初始值、依赖输入节点、对应差量规格场景(delta spec Scenario)和授权路径。
 - 任务节点候选信息必须声明父任务(Parent task)与内嵌原子任务(Atomic Tasks)的绑定:parent_task_id、execution_brief_artifact、execution_units_section、parent_local_atomic_task_queue、原子任务 ID 列表、执行顺序和审查状态。
 - 若一个技术 / 方案节点(TECH / SOL node)拆成多个任务节点,记录 `split_node` 图操作意图;若多个设计节点合并成一个执行批次,记录 `merge_nodes` 图操作意图。
 - 阶段门禁(Stage Gate)PASS 后由 `harness gate advance` 创建或更新任务节点,推进执行简报产物(promotion execution-brief artifact),把执行单元(Execution Units)中对应父任务的 `atomic_task_queue` 绑定到任务节点,随后重建 board / index / tree 并写入下一张任务切片(Mission Slice)。拆解工作流不直接编辑工作图(Work Graph)派生视图,也不手工改任务切片。
</step>

<step id="step-6" n="6" goal="一次性写盘 + 审查员派发">
 - 写盘前必须确认 Step 9 的智能体(Agent)实现条件已处理。若本任务涉及智能体能力,智能体实现任务项必须已经并入同一轮父任务 / 原子任务 / 测试义务(Parent task / Atomic Task / test obligation)设计;不得在审查员 PASS 后再追加智能体任务。
 - 写入 `harness-runtime/harness/artifacts/<mission-id>/breakdown/execution-brief.md`;这是唯一执行计划产物。写盘时每个父任务(Parent task)必须已包含 `atomic_task_queue.status: ready` 和至少一个原子任务详情(Atomic Task details)。
 - 硬门禁(Hard gate)`no-incomplete-brief-to-gate`:禁止写入"缺原子任务队列(Atomic Task Queue)、等待 writing-plans 补齐"的执行简报(execution-brief)作为阶段门禁(Stage Gate)候选产物。若队列缺失或不完整,继续在拆解阶段(breakdown)内修复;无法补齐时发起决策门禁(Decision Gate)或返回 BLOCKED。
 - 若 `contracts/execution-brief.contract.yaml` 不存在,调用 `harness contract init --mission <mission-id> --stage breakdown --template execution-brief --json` 初始化;若已存在只能 patch。
 - 将任务项 action contract 字段、全部执行角色的 execution_results[] 写入 contract 的 control_contract。
 - 写盘完成后,并行调用角色策略(role policy)返回的全部审查子 Agent(review roles);默认至少调用 `execution-plan-effectiveness-reviewer`。
 通过 `@execution-plan-effectiveness-reviewer` native delegation调用 `execution-plan-effectiveness-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
 - 任务信封(Task Envelope):已写入的 execution-brief 路径(每个父任务都含 `atomic_task_queue`)、外部动作契约(action contract)路径、证据图义务(Evidence Graph obligations)、只读约束和停止条件(stop conditions);审查结论由审查员返回 `role_verdict` 建议,主流程经 `harness contract record-review --artifact harness-runtime/harness/stages/${mission-id}/contracts/execution-brief.contract.yaml --role execution-plan-effectiveness-reviewer --verdict <PASS|PASS_WITH_RISK|HOLD|BLOCKED> --subagent-id <dispatch-id> --model <resolved-model> --review-basis harness-runtime/harness/artifacts/${mission-id}/breakdown/execution-brief.md --summary <review-summary> --json` 写入 `role_verdicts` 并同步维护审查轮次。
 - 循环:id=reviewer-loop;无轮次放行(producer-fixable 缺口不设通过上限,轮次只记录修复历史);退出条件:execution-plan-effectiveness-reviewer 在等同严格度下返回 PASS / 无阻断
  - 每轮审查返回后通过上面的 `harness contract record-review` 记录 verdict；不再用 `patch --add-round` 手工维护轮次。
  - 分支:审查结论
   - 情况:HOLD / BLOCKED
    - 按审查员返回的 `finding_type` 分流处理,不一律在 breakdown 内就地改 brief 措辞:
     - **回产出者(carrier 回 delivery-slicer / test-planning-expert)**:`finding_type ∈ {missing_iteration_authorization, risk_order_missing, unsplittable_parent_task, hidden_dependency, weak_test_obligation}` 属实质切片 / 排序 / 追溯 / 测试义务缺陷,重新派发 `delivery-slicer` 子 Agent(必要时并行 `test-planning-expert` 子 Agent)重做相应父任务 / 原子任务 / 测试义务,再按 Step 1 合并义务矩阵重出拆解规划包(breakdown planning packet)。其中 `weak_test_obligation` 必须带上 `test-planning-expert` 子 Agent 一并重做。主流程仅在缺陷确属纯格式 / 引用路径笔误时就地改 brief。
       通过 `@delivery-slicer` native delegation调用 `delivery-slicer` subagent（Cursor auto-routes 到对应 agent registry 项）
       通过 `@test-planning-expert` native delegation调用 `test-planning-expert` subagent（Cursor auto-routes 到对应 agent registry 项）
     - **补 vs 澄清分流(回流上游 / 决策门禁)**:`finding_type ∈ {upstream_design_gap_masked, scope_leak}` 表示缺口本质是上游设计缺失 / 越权或需澄清,不在 breakdown 内就地改 brief 硬编理由。按 Step 0 输入合格性枚举回流对应上游阶段(`return_to_prd` / `return_to_solution` / `return_to_tech_design` / `return_to_interaction` / `return_to_agent_capability_design`),或在归属不明 / 需用户裁决时发起决策门禁(Decision Gate,`harness approval append --type tradeoff`)。
    - 上述任一分流完成后,立即重新派发审查员(reviewer)做全量审查。
    - Hard gate `no-skip-recheck`:
     - 修复完成 ≠ 审查通过。只有审查员确认无阻断且 `pending_reviewer_recheck=false` 才能退出。
     - Enforced by: hook=breakdown-check-pending-recheck
   - 情况:PASS
    - 退出循环。
 - 条件:卡死——同一阻断在重做相应父任务 / 原子任务后,审查员仍以相同根因连续 HOLD 且无实质进展(按缺口本质判断,不是"轮次到点")
  - **可操作判据**:连续 2 轮审查员的 `blocking_gap` 指向同一 obligation ID 且 `finding_type` 相同、且 producer(delivery-slicer / test-planning-expert)本轮 diff 未触及该 obligation 对应章节 → 判定卡死(由 record-review 已存的 verdict 历史程序化比对前后两轮即可识别)。据此区分"修了措辞没修实质"(diff 未触及对应章节 = 仍卡死)与"真有实质进展"(diff 已改对应章节 = 未卡死,继续循环)。
  - 不得降级通过。按 `core.md`「严格审查不变量」重新归因:producer 能补但反复没补对 → 留在修复循环升级修复策略继续重做;本质是上游设计缺失 / 需澄清 → 按 `finding_type` 回流对应上游阶段或发起决策门禁。
  - 仅当确需用户在路线 / 范围上拍板才能解时,调用 tool: `AskUserQuestion`。
   - 问题:拆解阶段以下阻断在反复重做后仍无法在当前范围内解决(已附完整未解决阻断清单与卡点根因),需要你决策方向
   - 候选答案(**不含"接受当前简报 / 降级通过"**):
      - 给出修复方向,留在审查循环继续重做
      - 回技术设计(tech-design)修订
      - 回 design 阶段
      - 升级 BLOCKED,终止本阶段
  - 把答复经 `harness approval append --type breakdown_user_checkpoint --stage breakdown --answer <enum>` 写入类型化载荷(typed payload),不得直接落 markdown。残留风险只能由用户在充分披露完整未解决阻断后于 Decision Gate 显式拥有并记 approval,审查循环本身永不把未解决阻断自动转为通过。
</step>

<step id="step-7" n="7" goal="质量自检(中间 lint,可重复调)">
 - 调用 cli `harness execution-brief self-check` `--mission ${mission-id}`,evidence=required。
 - 逐项检查:每个本轮范围内的 `SUC-xx-OP-xx` 是否至少对应一个父任务或原子任务;每条验收场景 / 条件(AC 仅作追溯锚点)是否至少对应一个任务项输出;任务项顺序是否合理;每个任务项测试要求是否足够具体;每个任务项是否在动作契约(Action Contract)声明必需证据(required evidence)和测试义务(test_obligation);每个父任务(Parent task)是否有内嵌 `atomic_task_queue` 且每个原子任务(Atomic Task)有同 ID 详情块;每个任务项 `traces_to` 是否引用真实存在的 ID;执行者是否只靠执行简报(execution-brief)即可理解边界并进入派发计划(dispatch plan)生成;`spec.enabled=true` 时差量规格每个 ADDED/MODIFIED Scenario 是否都有任务项引用且"规格引用"路径真实存在。
 - 条件:本 mission 有原型产物(behavior-graph.yaml 存在)
  - 原型覆盖检查:behavior-graph.yaml 中每个本 mission page_state(`PS-<surf>-<state>`)是否被某任务项 `traces_to` 覆盖。机器判定由阶段门(gate run / alignment check)执行;未被任何任务覆盖的 `PS-` 触发 FAIL 级 `PAGESTATE_NOT_COVERED`(分母为 mission-local)。
  - e2e 断言义务覆盖检查:behavior-graph.yaml 中每个 `e2e_obligation=true` 的 edge 须被某含 UI 任务项的 e2e 义务(Step 3b 声明的 `edge.testid`)覆盖,否则验证阶段(verify)的 `harness verify prototype-alignment-check` 会报 `PROTOTYPE_E2E_EDGE_NOT_ASSERTED`;testid 占位 / 缺失报 WARN `E2E_OBLIGATION_EDGE_NO_TESTID`。拆解阶段应在写盘前确保每条 `e2e_obligation` 边都有承载任务的断言义务,把"实现了但没人验证界面对不对"挡在 breakdown。
  - 合法出口:确不覆盖某 `PS-` 或某 `e2e_obligation` 边时,经决策门禁显式改写后在契约 `prototype_coverage_exemptions: [{id, reason}]` 登记,理由缺失报 `PROTOTYPE_EXEMPTION_NO_REASON`;不得静默漏覆盖。
  - 非破坏:非 UI / 未跑 interaction 的任务无 behavior-graph,本检查自动跳过。
 - 条件:发现缺口
  - 如果缺口属于拆解阶段(breakdown)自身产物问题(任务粒度、任务顺序、证据要求、停止条件 stop_if、原子任务详情 Atomic Task detail、授权路径表达不清),在本阶段修复。
  - 如果缺口属于上游定义不足(验收场景 / 条件缺失、方案路线不成立、模块 / 接口 / 数据设计不清、风险验证方式缺失、智能体能力边界不清),停止修执行简报(execution-brief),回流到对应上游阶段;不得在拆解阶段内静默补设计。
</step>

<step id="step-8" n="8" goal="产物门禁(Artifact Gate)自检(人类可读 checklist)">
 - Step 7 自检(self-check)+ Step 10 `harness execution-brief gate run` 已合并为单一阶段化门禁(phase 化 gate,quality_check + artifact_gate)。本步骤保留作为人类可读清单(checklist),机器判定以 gate run 输出为准。
 - 验证 execution-brief.md 包含必要结构:任务目标、硬性约束、任务项(带 checkbox 且每个任务项有完成边界)、完成定义(Definition of Done)。
 - 验证 execution-brief.md 前部包含 `Contract: contracts/execution-brief.contract.yaml` 引用,且不包含 fenced YAML contract / ## action_contract / ## execution_result / ## role_verdicts 段落。
 - 验证外部 contract 包含 `control_contract.type: action_contract`,且每个任务项有 traces_to / required_evidence / tdd_scope / test_obligation / stop_if。
 - 验证本文件包含执行单元(Execution Units)、每个父任务(Parent task)的父任务本地 `atomic_task_queue`、每个原子任务(Atomic Task)的同 ID 详情标题;缺失则 FAIL: missing_atomic_task_queue / missing_atomic_task_detail。
 - 调用 cli `harness contract check` `--artifact harness-runtime/harness/artifacts/${mission-id}/breakdown/execution-brief.md`,evidence=required。
 - 条件:结构不完整
  - 自行补充缺失部分,不要跳过。
</step>

<step id="step-9" n="9" goal="条件:为智能体(Agent)实现规格生成任务项">
 - 条件:agent_engineering.enabled=true
  - 参考 `docs/methodologies/agent-capability-engineering.md` §6(正确工作顺序)。
  - 读取 `harness-runtime/harness/artifacts/<mission-id>/technical-analysis/tech-design.md` 的 `## Agent 实现` 段落(由 `agent-capability-designer` 产出并经 `agent-capability-reviewer` 审查)。
  - 条件:tech-design.md 存在智能体(Agent)实现规格
   - 对每个智能体组件生成对应实现任务项,并在 Step 6 写盘与审查员派发前并入同一轮执行简报(execution-brief):实现智能体定义文件 / 实现技能 / 工具 / MCP 承载物 / 实现 policy/hook 制度层约束 / 接入 runtime / 编写评估(eval)测试脚本。每个任务项 `traces_to` 至少引用一个 tech-design ID 或 `## Agent 实现` 段落稳定组件 ID。
   - 智能体任务必须参与同一轮切片、测试义务设计和 `execution-plan-effectiveness-reviewer` 审查;如果审查员 PASS 后才发现需要新增智能体任务,必须回 Step 3 重新切片并重审。
  - 条件:`agent_engineering.enabled=true` 但 tech-design.md 缺少智能体实现规格
	   - HALT:返回设计阶段调用子 Agent `agent-capability-designer` / `agent-capability-reviewer` 补齐 `## Agent 实现`,不得自行发明 capability-specs 目录。
</step>

<step id="step-10" n="10" goal="阶段退出门禁(Stage exit gate)">
 - 调用 cli `harness alignment check` `--mission ${mission-id} --stage breakdown`,evidence=required。
 - 对齐检查(alignment check)校验任务 / 原子执行单元(tasks / atomic units)追溯到 `SUC-xx-OP-xx`、验收场景 / 条件(AC 仅作追溯锚点)、领域命令(domain command)、不变量(invariant)、状态迁移(state transition)、技术设计 ID(tech-design IDs);本 mission 有原型产物时,还校验每个 page_state(`PS-`)被某任务 `traces_to` 覆盖,未覆盖且未登记 `prototype_coverage_exemptions` 报 FAIL 级 `PAGESTATE_NOT_COVERED`;程序化 FAIL 必须回拆解阶段(breakdown)修正,不得由审查员(reviewer)覆盖。
 - 调用 cli `harness execution-brief gate run` `--mission ${mission-id}`,evidence=required。
 - 只有 `phase_results` 中 `quality_check` 与 `artifact_gate` 双双 PASS、且 `failed_checks` 为空,才可推进。
 - 硬门禁(Hard gate)`gate-pass-before-complete`:未 gate PASS 前不得调用 `harness mission stage complete breakdown`;`breakdown-check-gate-pass` hook 物理阻断;M2.1 CLI 是该 gate 的唯一入口。
 - 调用 cli `harness mission stage complete breakdown` `--mission ${mission-id}`,evidence=required。
</step>

</steps>

<failure_paths>

| 失败类型(Failure) | 触发条件(Trigger) | 处理方式(Handling) |
|---|---|---|
| `upstream-input-insufficient` | 产品定义包、solution、tech-design、interaction 或智能体(Agent)能力设计不足以支撑执行授权 | 停止拆解;按缺口类型回流产品定义 / 方案 / 技术分析 / 智能体能力设计,不得在执行简报(execution-brief)内补造设计。 |
| `worker-blocked` | `delivery-slicer` 或 `test-planning-expert` 返回 BLOCKED | 在外部契约(contract)写入 `execution_results[].status=BLOCKED`,记录关注点(concerns),发起决策门禁(Decision Gate,`harness approval append --type tradeoff`)。 |
| `parallel-barrier-violation` | 仅一个并行 worker 返回 DONE | barrier 未达成,breakdown-check-barrier-complete hook 阻断 stage advance;重新派发缺失角色或 BLOCKED。 |
| `reviewer-blocked` | `execution-plan-effectiveness-reviewer` 返回 BLOCKED | 按 finding_type 重新归因；需用户拍板时触发 AskUserQuestion，候选(**不含"接受当前简报 / 降级通过"**):继续重做 / 回技术设计(tech-design)/ 回设计阶段(design)/ 升级 BLOCKED。残留风险仅由用户在 Decision Gate 显式拥有并记 approval。 |
| `review-stuck` | 同一阻断在重做后仍以相同根因连续 HOLD 且无实质进展(非轮次到点) | 重新归因:producer 能补则继续重做;上游缺失则按 finding_type 回流;需用户拍板则 AskUserQuestion（候选仅:继续重做 / 回 tech-design / 回 design / 升级 BLOCKED,不含降级通过）。残留风险仅由用户在 Decision Gate 显式拥有并记 approval。 |
| `contract-check-fail` | harness contract check --upstream 返回 FAIL | 按 FAIL code 修复 traces_to / atomic_task_queue / required_evidence 后重审。 |
| `spec-coverage-fail` | harness execution-brief check-coverage --spec-mode strict 返回 FAIL | 补任务项覆盖未覆盖 Scenario;若 Scenario 不应实施则回产品定义阶段修订差量规格。 |
| `agent-engineering-halt` | step-9 触发 HALT(tech-design 缺智能体实现规格) | 回设计阶段(design)补齐;不在拆解阶段(breakdown)内自行发明 capability-specs。 |
| `agent-task-after-review` | 审查员 PASS 后才发现需要新增智能体(Agent)实现任务 | 回 Step 3 重新切片,把智能体任务并入同一轮测试义务和审查员判断。 |
| `risk-order-missing` | 父任务(Parent task)顺序没有优先处理会影响后续实现成立的架构 / 数据 / 权限 / 集成风险 | 在拆解阶段内重排任务;若风险验证方式缺失则回技术分析。 |
| `parallel-write-scope-conflict` | 两个 worker 输出的 `tasks[].authorized_paths` 并集出现重叠且未声明依赖 | 回技术设计(tech-design)或在拆解阶段内拆分任务 / 标记 `must_serialize`。 |
| `writing-plans-boundary-violation` | 在 stage!=breakdown 或非 --mode internal-carrier 时调用 writing-plans | breakdown-check-writing-plans-boundary hook 阻断;若用户手动 --manual-replan 必须带 trace-log 留痕。 |

</failure_paths>

阶段流转(Stage transition):

- 决定来源:任务切片(Mission Slice)中的 `control_plane.stage`,来自工作图(Work Graph)。
- 典型下一步:
  - `execute`:执行简报门禁(execution-brief gate)PASS,任务节点(TASK node)已就绪
- 强制入口:cli=`harness gate advance`

</workflow>
