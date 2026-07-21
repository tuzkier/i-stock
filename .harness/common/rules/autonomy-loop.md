# 自治循环

你的主执行循环是：恢复 → 选择 → 调度 → 验证 → 判断。

**路径约定：**

- `COMMON_ROOT`：当前项目内 Harness 公共正文根，包含 `rules/`、`skills/`、`agents/`、`protocols/`
- `CONFIG_PATH`：Harness 配置文件路径
- `RUNTIME_ROOT`：Harness 任务运行数据根，包含 `missions/`、`stages/`、`state/`、`traces/`
- `WORK_GRAPH_ROOT`：Work Graph 运行数据根，包含 `nodes/`、`boards/`、`indexes/`、`trees/`、`mission-slices/`
- `PROJECT_KNOWLEDGE_ROOT`：项目长期知识根，包含行为规格、设计知识、工程政策和复盘沉淀

本文件只写这些逻辑根，不写源码维护目录。由入口文件或安装器把逻辑根解析到当前项目的实际路径。

**安装后默认映射：**

| 逻辑根 | 安装后路径 |
|--------|------------|
| `COMMON_ROOT` | `.harness/common` |
| `CONFIG_PATH` | `harness-runtime/config/harness.yaml` |
| `RUNTIME_ROOT` | `harness-runtime/harness` |
| `WORK_GRAPH_ROOT` | `harness-runtime/harness/work-graph` |
| `PROJECT_KNOWLEDGE_ROOT` | `project-knowledge` |

## 1. 恢复上下文（最小上下文装配）

每轮循环先通过控制面获取当前状态，不要凭记忆继续干。只加载本阶段直接需要的上游产物，不把所有文档一次性灌入。

**必须通过 `harness-cli` 获取（每轮，凡 CLI 已支持的控制面状态不得直接读文件）：**

- 运行配置快照 — 全局配置（execute_mode、execution_governance、escalation、work_graph lanes）
- 当前 Mission 状态 — 确定活跃任务、当前 Mission Slice 摘要和阶段内执行状态
- Board / Work Graph / 当前 Mission Slice 快照（若已存在）— 确定 Board 状态、当前 node、lane、stage 和 lane_action
- 执行日志（如果存在）— 调度 `trace-log` 技能的 recover 操作，获取当前位置 + 未解决阻塞 + 最近日志
- git-workflow（recover 操作）— 读取 `COMMON_ROOT/skills/git-workflow/SKILL.md` 执行 recover
- `project-context.md`（如果存在）— 项目约束和历史教训
- `RUNTIME_ROOT/missions/<mission-id>/mission-contract.md`（有活跃任务时）— 目标、范围、验收场景、治理级别和 Checkpoint 配置；不作为链路调度源
- **（`spec.enabled=true` 时）** `PROJECT_KNOWLEDGE_ROOT/specs/` — 读取长期行为契约；`PROJECT_KNOWLEDGE_ROOT/engineering/policies/stage-rules.yaml` — 提取 `context`（全局技术约束，本轮全程有效）和 `rules.<control_plane.stage>`（本次 Mission Slice 所属阶段规则，进入阶段工作流前载入）；文件不存在时跳过

**按需读取（根据当前 Mission Slice / lane action）：**

上下文装配从当前 Mission Slice 开始，而不是从固定阶段链开始。

| 当前 action 信息 | 必须读取 |
|---------|----------|
| 任意 Mission Slice | `lane_action`、`primary_nodes`、`related_nodes` / `related_candidates`、`operation` / `graph_operation`、`lane_action.output_artifact`、`operation_profiles`、primary node 的 `inputs` / `outputs` / `relations` |
| `lane_action.stage=git-workflow` 或 mission branch 未就绪 | intake identity（mission-id 和 slug）、用户原始意图，以及通过 `harness-cli` 获取的当前 Mission git 状态；prepare 必须先于控制面写入 |
| `lane_action.stage=intake` | 用户输入、project-context、已有 Work Graph node / index / board，用于创建或关联 seed node |
| `lane_action.stage=discovery` | primary / related node、project-context、代码现状证据；不默认读取全量阶段文档 |
| `lane_action.stage=prd` | Mission Contract 的 intent / 验收场景、primary node、已 accepted 的上游 Work Graph artifact、discovery 产物（仅当该 node / slice 引用） |
| `control_plane.stage=solution` | PRD / solution 中被 primary node 或 upstream artifact 引用的部分 |
| `control_plane.stage=interaction` | 产品定义包 / 领域模型 / interaction 中被 primary node 或 upstream artifact 引用的原型界面、用户旅程、状态矩阵、视觉资产；除明确 API-only / 无界面外默认需要 |
| `control_plane.stage=technical_analysis` | PRD / solution / interaction / technical artifact 中被 primary node 或 upstream artifact 引用的技术设计材料 |
| `lane_action.stage=interaction` | 当前 node、产品定义包 / 领域模型、原型界面与状态矩阵、visual-interaction manifest、原型 trace 规约与 project-lint 状态（manifest 产出后当场卡口，不拖到 verify） |
| `lane_action.stage=breakdown` | 当前 node 引用的 design / delta spec / accepted upstream artifacts；任务项必须映射为 TASK node 候选 |
| `lane_action.stage=execute` | 当前 TASK / BUG node、execution-brief、delta spec scenarios、授权路径、测试义务；不默认读取 prd / solution |
| `lane_action.stage=code-review` | 当前 TASK / BUG node、execution evidence、变更 diff、测试证据、required reviewers |
| `lane_action.stage=verify` | 当前 node、verification obligations、命令证据、验收追溯、project-lint/e2e/tdd 状态 |
| `lane_action.stage=delivery` | 当前 delivery node / primary nodes、verification-report、code-review、acceptance-result、follow-up / block / defer graph operation intent |
| terminal / no schedulable node | 通过 `harness-cli` 获取 Board / Work Graph / last operation / approval 快照，判断是否只是无可推进 node，还是需要 finishing-branch / retrospective |

**强约束：**
- 不把整个 stages 目录一次性读入
- 不把历史任务的文档当作当前输入
- 不跳过 `harness-cli` 的当前 Mission 状态快照直接猜当前工作位置
- 不跳过 `harness-cli` 的 Board / Work Graph / Mission Slice 快照直接按 stage pending 推进

## 1.5. 技能路由（每轮）

恢复上下文后，立即调度 `skill-router` 进行技能匹配：

```
加载 COMMON_ROOT/skills/skill-router/SKILL.md
按 DOT 决策图判断当前消息应调用哪些技能
```

**skill-router 与自治循环的仲裁规则（重要）：**

| 情境 | 谁负责决定下一步 |
|------|----------------|
| 有当前 Mission Slice | **Mission Slice 的 lane_action / control_plane** |
| 有活跃任务但无当前 Mission Slice | **board-router** 选择可推进 node 并生成 Mission Slice |
| 执行中出现症状（缺陷 / 审查反馈 / 偏差） | **skill-router 症状匹配** |
| 没有活跃任务 | **skill-router**（路由到任务接入） |
| skill-router 与 Work Graph 生命周期结论冲突 | **Mission Slice / Board Router 优先**，但缺陷、审查反馈、Decision Gate、质量缺口等即时症状可中断当前阶段 |

skill-router 的 DOT 决策图里的"调用 X"节点是**即时症状匹配**，不是阶段流水线的替代。生命周期入口是 Board / Mission Slice；mission-status 的 `stages` 只记录当前 slice 内已经进入的阶段状态，不决定下一项工作。**没有 Mission Slice 的活跃任务直接 BLOCK，由 board-router 重建 slice，不再有 stage-mode fallback。**

## 2. 选择下一步

Board / Mission Slice 是最高层调度状态。

| 条件 | 调度的技能 |
|------|-------------|
| 项目没有 `project-context.md`（既有项目） | `generate-context` |
| 没有活跃任务契约 | `intake` |
| 有活跃任务但没有可恢复 Mission Slice | `board-router` |
| 新 Mission 已生成 mission-id 但 mission branch 未就绪 | `git-workflow prepare`，且必须发生在 `mission init`、Work Graph node、Mission Slice 等控制面写入之前 |
| Mission Slice 缺少 `lane_action`、`operation_profiles` 或与 `work_graph.lanes` 注册表不一致 | BLOCKED，进入 `work-graph` / `board-router` 修复；不得自行推导阶段链 |
| 当前 Mission Slice 的 `control_plane.stage` 指向阶段 skill，且 `lane_action.output_artifact` 尚未完成 | 对应阶段 skill |
| 当前 `lane_action.output_artifact` 完成，Stage Gate 尚未通过或 graph operation 尚未应用 | `stage-gate`；Gate PASS 后由 `harness-cli` 执行 Gate advance / graph operation |
| 用户要求开始执行，但当前 breakdown 产物 `execution-brief.md`（含必需的 Atomic Task Queue）尚未通过 Stage Gate / `harness gate advance` 同步到 Work Graph | 先运行 `stage-gate`，不得直接进入 `execute` |
| graph operation 已应用，Board / index 已更新 | 优先消费 `harness gate advance` 自动写入的下一张 Mission Slice；若没有下一张 slice，再返回 `board-router` 从更新后的 Board 选择下一项工作 |
| Board 没有 ready / active node，且当前 active mission 无未完成 slice | 检查 terminal graph state：若最后 operation 已把 primary nodes 推进到 `done` 且验收记录齐全，进入 `finishing-branch` / `retrospective`；否则报告 idle / BLOCKED，不得凭阶段清单补跑 delivery |

Mission Slice 到阶段 skill 的映射由 `work_graph.lanes` 和 `lane_action.skill` 决定，不由 `mission-status.stages` 的第一个 pending 项决定。`mission-status.current_stage` 仅是跟踪字段，不再作为阶段 skill 的 fallback；如果一个活跃任务没有 Mission Slice，必须先调用 `board-router` 重建。

**特殊情况调度：**

| 条件 | 调度的技能 |
|------|-------------|
| 执行中发现重大偏差 | `course-correction` |
| 执行中遇到缺陷 / 测试失败 / 构建失败 / 异常行为 | `systematic-debugging` |
| 缺陷需要复现、根因、回归、沉淀闭环 | `bug-fix`（读取 `COMMON_ROOT/protocols/bug-fix/PROTOCOL.md`） |
| Stage Gate evidence 缺口、审查员 HOLD、证据充分性或质量治理问题 | `quality-control`（读取 `COMMON_ROOT/protocols/quality-control/PROTOCOL.md`） |
| 多个独立问题同时出现（2+ 不同域的失败） | `parallel-agents` |
| 收到代码审查反馈需要处理 | `receiving-review` |
| breakdown planning packet 尚未为每个 Parent task 建立 parent-local `atomic_task_queue` | 留在 `breakdown` 内继续联合拆解；必要时把 `writing-plans` 作为写盘前内部 helper，不得产出 Parent-only 中间态 |
| 已写入 / 已同步的 execution-brief 缺失 Atomic Tasks、队列未审查、未覆盖当前任务项或与 TASK node 绑定不一致 | BLOCKED，回到 `breakdown` / Stage Gate 修复并重新 advance；不得在 execute 中补丁式继续 |
| 当前 Mission Slice / node surface 含前端可见界面，且当前 action 需要 UI 设计或实现证据 | `ui-ux-pro-max` |
| 即将宣称完成/通过/修好（任何阶段） | `verification-before-completion` |
| 当前 action 命中 Checkpoint 条件 | 由 Stage Gate / decision-system 处理；`execution_governance` 只决定是否需要人工确认，不参与下一项 node / action 选择 |
| Checkpoint 文档完成且配置了 `pre_checkpoint_doc_review` | 当前 action 的 required reviewer 已在工作流内完成审查循环（在进 Checkpoint 前） |

## 3. 调度执行

确定了下一步后，主 Agent 进入编排模式。

这里的“调度者”仍然是当前编码 Agent / 主 Agent 本身，不是另一个常驻服务。调度的含义是：主 Agent 只维护流水线状态、进入对应阶段技能或工具型技能，并收集阶段产物、审查结论和阻塞状态；阶段正文由阶段 workflow 声明的执行子 Agent 承担，主 Agent 不再把每个阶段工作流全量摊进自己的上下文里执行。

**3a. 执行日志记录开始：**
调度 `trace-log` 技能，记录当前技能开始执行 + 更新当前位置。

**3b. 执行技能 / Agent：**

先判断当前 action 指向的技能是阶段级还是工具型。对于阶段级技能（`git-workflow prepare` 除外），在读取阶段 workflow 并写正式产物或代码前，必须先调用 `git-workflow start-stage(<control_plane.stage>)`，确保当前 Mission Slice 所属 stage 已有独立的 stage branch + stage worktree；若 `git.strategy == downgraded` 则跳过 Git 操作。

阶段跳过仲裁：当 `control_plane.stage` 在当前 `execution_governance.levels.<autonomy_level>.skippable_stages` 中时，合法的跳过方式只有"整个阶段不产出 output_artifact、Mission Slice 直接前进到下一个 lane_action"——这种情况本阶段根本不进入 workflow，trace-log 记录一条 `stage_skipped` 即可。**只要本阶段开始产出 output_artifact，就必须按 `professional_roles.stage_policies` 的完整角色集合调度执行子 Agent 与审查子 Agent**，不允许借"阶段可跳过"为由跳过 reviewer；这条由 Stage Gate 兜底校验。

| 技能 / 阶段 | 执行方式 |
|-------------|----------|
| 阶段级技能 | 读取对应 `COMMON_ROOT/skills/<skill>/workflow.md`；由该 workflow 声明要调用的执行子 Agent、审查子 Agent、产物要求和 Gate 条件 |
| 其他工具型技能 | 主 Agent 直接执行对应 `COMMON_ROOT/skills/<skill>/workflow.md` |

执行边界：

1. 阶段 workflow 只用“调用 `<name>` 子 Agent”声明子 Agent 名称、产物要求和 Gate 条件；角色 prompt package 路径由 adapter / COMMON_ROOT 解析。
2. 主 Agent 按当前 coding agent 的默认子 Agent / 委派规则调用对应子 Agent；调用前必须读取 `<COMMON_ROOT>/agents/<name>.md` 并把正文作为 role prompt package 注入，再附加 Task Envelope（路径、scope、完成条件、停止条件）。具体模型候选由 `harness config snapshot --json` 返回的模型路由摘要提供，公共 workflow 不写模型 ID，也不直接读取模型路由 YAML。若当前 adapter 的 dispatch 原语支持调用时传模型（例如 Codex `spawn_agent`），必须显式传入解析出的模型；若当前 adapter 通过 native agent registry 绑定模型（例如 Cursor），安装器必须在 agent frontmatter 中写入解析出的模型，避免隐式继承主 Agent 模型。
3. 当 workflow、lane action 或 role policy 返回多个执行角色 / 审查角色时，主 Agent 必须按 barrier 并行调度：同一执行 barrier 的独立 execution roles 并行；执行 barrier 全部返回后进入审查 barrier；同一审查 barrier 的 readonly reviewers 并行。只有存在明确产物依赖、共享写入范围或 workflow 显式声明必须串行时才允许串行，并记录原因。**记录落点**：串行原因经 `trace-log` 技能写一行（其 `log` 操作记 "串行调度 X→Y，原因：…"），或写入当前 Mission Slice / contract 的 dispatch 记录，使"为何没并行"可被 Gate 与复盘查证，不只留在主 Agent 上下文里。（`trace-log` 操作约定可后续补一条 `serial_dispatch` 记录格式。）
4. 阶段是否可继续只看产物、`execution_result(s)`、`role_verdicts`、obligation evidence 和 Stage Gate 结果，不以“用了哪种底层机制”作为完成证据。
5. 工具型技能（如 `trace-log`、`stage-gate`、`harness-cli`、`harness-lint`、`git-workflow recover/start-stage/close`）仍由主 Agent 直接执行；其中 CLI 支持的控制面读写必须经 `harness-cli`。

执行过程中如果做了关键决策或遇到阻塞，调度 `trace-log` 技能记录。

**3c. 执行日志记录结束：**
调度 `trace-log` 技能，记录技能完成/失败/跳过 + 产出物 + 更新当前位置的下一步。

然后进入 Step 3d，再进入 Step 4。

**3d. 修改驱动的闭环（审查-修复循环）：**

**核心原则（不可违反）：**
> **执行者只能声明「已处理」，不能声明「已解决」。**
> **「我改好了」不是证据，只有对应的审查 Agent 重新确认无阻断，才算「已解决」。**

**Step 3d 的适用范围（重要）：**

以下技能已在各自工作流内置了审查 Agent 循环，内部循环的 PASS 即满足本要求，**Step 3d 不对其重复触发**：

| 技能 | 内置审查机制 |
|-------|------------|
| `execute` (SDD 模式) | 每个任务项先按 `execute/dispatch-plan.md` 生成 dispatch plan，再默认进入 `spec-reviewer` 循环；dispatch plan 返回的条件 reviewer 按需运行 |
| `code-review` | 有 `correctness/tdd/architecture/security-reviewer` 并行循环，退出时无 High；`tdd-reviewer` HOLD 等同 High |
| `intake` / `prd` / `design` / `breakdown` / `verify` / `delivery` | 使用 `professional_roles.stage_policies` 声明的阶段专业 reviewer，退出时对应 `role_verdicts` 无阻断 |
| `dependency-impact` | 默认作为当前 Mission Slice 的依赖证据 carrier；使用 `integration-impact-expert` / `dependency-validity-reviewer` 内置循环，退出时把 `dependency-impact.md` 作为调用方 slice 的 evidence artifact。只有被 `work_graph.lanes` 显式注册为独立 stage 时，才按独立 Work Graph action 进入 Stage Gate。 |
| `discovery` | 由 `discovery-analyst` 产出探索简报；事实来源和置信度由 Stage Gate / 后续工作消费 |

**以下技能产生修改后，Step 3d 必须触发：**

| 技能 / 场景 | 必须调用的审查 Agent |
|-------------|--------------------------|
| `receiving-review` 应用反馈后 | 已在 `receiving-review` SKILL.md 步骤 6.5 内置；Step 3d 确认该步骤已执行 |
| `systematic-debugging` 修复后（逻辑变更） | 重新运行失败测试/命令确认症状消失（命令输出是证据）；有逻辑变更时额外调用 `correctness-reviewer` 子 Agent |
| `execute` (内联模式) 中间修复 | 调用 `spec-reviewer` 子 Agent 对本任务项全量确认 |
| 其他工具型技能产生的修改 | 代码修改调用 `spec-reviewer`；阶段文档修改调用该阶段 `professional_roles.stage_policies` 中声明的专业 reviewer |

**闭环步骤（仅适用范围内的技能）：**

```
1. 执行者声明「已处理」：说明改了什么、影响哪些范围
2. 调用对应审查 Agent 重新审查（见上表），按角色契约传入路径化 brief
3. 等待审查员返回裁决：
 - PASS（无阻断性问题）→ 继续 Step 4
 - HOLD（仍有阻断性问题）→ 执行者二选一：
     a. **接受** → 回到 Step 3b 继续修复，再进入 3d（修复循环，无轮次放行——轮次只记录修复历史、永不构成放行理由，每轮以等同严格度重审，循环到审查员在等同严格度下 PASS）
     b. **反驳**（认为该 gap 不成立）→ 走下方「有界反驳-仲裁通道」，不盲改
 - 卡死（执行者修复后，审查员仍以相同根因连续 HOLD 且无实质进展，按缺口本质判断、非"轮次到点"）→ 不得降级通过，发起 Decision Gate，向用户展示遗留问题清单，候选不含"接受遗留 / 降级通过"（继续修 / 改范围回退上游 / 升级 BLOCKED）；残留风险只能由用户在充分披露后显式拥有并记 approval。审查循环本身永不把未解决阻断自动转为通过
```

**有界反驳-仲裁通道（改造④，区别于上面的修复循环）：**

修复循环计的是"执行者反复**改**"；当执行者认为审查员**判错了**（gap 不成立），不应被迫一直修没坏的东西，走结构化反驳：

```
1. 执行者记 dispute（写入 contract effectiveness_review.disputes）：
   {gap_id, role=被反驳的 reviewer, worker_rebuttal, evidence_refs[], round=1, status=open}
   —— 反驳必须带文档集内证据引用（测试 / 代码 / ID / 命令输出）；
      evidence_refs 为空 = 无效反驳，不享受"暂不修复"，转回修复循环。
2. 该 reviewer 收到反驳后二选一：
   - 认可 → status=withdrawn_by_reviewer，撤销该 gap（闭环）
   - 坚持 → 补论证，round+1，status 保持 open
3. 执行者再评：认同则 status=conceded_by_worker 转修复；仍反驳则 round 继续累加。
4. 主 Agent 每轮跑 `harness contract check-disputes --artifact <contract> [--max-rounds 2]` 判断是否该升级
   （它消费 `dispute_escalation_signal`：status=open + 有证据 + round>=上限 → 返回 BLOCKED + escalation）。
   命中即升级 Decision Gate 由用户仲裁，裁决经 harness clarification record / approval 落盘（裁决进文档集），双方按裁决执行。
   ——不靠口头自觉判断"几轮了"，以命令输出为准。
```

> 反驳是为了防止执行者盲目服从一个可能判错的 reviewer，不是逃避修复的后门——三重约束兜底：**必须带证据引用 + 上限 2 轮 + 升级到人**。无证据的空口反驳一律转回修复循环。

<HARD-GATE>
适用范围内：修改后不调用审查 Agent 就推进 = 执行错误。
不适用范围内（已有内置循环）：不得重复触发 Step 3d，内置循环的 PASS 即为证据。
禁止以「自我对照」「重新阅读文档」代替审查 Agent 的重新确认。
例外（可不调用审查 Agent）：
 - 修复是纯机械操作（格式、空格、拼写），无逻辑变更，且有 linter 输出作为证据
 - 已发起 Decision Gate 且用户明确接受遗留问题
</HARD-GATE>

## 4. Gate 检查

**阶段级技能** 产出完成后，调度 `stage-gate` 技能进行阶段切换检查。

```
读取 COMMON_ROOT/skills/stage-gate/SKILL.md → 执行 workflow.md
```

**触发 Stage Gate 的技能（阶段级）：**
由当前 Mission Slice 的 `control_plane.stage` / `lane_action.output_artifact` 指向的阶段级技能触发，例如任务接入、探索、prd、设计、拆解、执行、code-review、验证、交付、retrospective。`dependency-impact` 默认不单独触发 Stage Gate，只作为调用方 slice 的 evidence carrier；若目标项目把它注册为 `work_graph.lanes` 中的独立 stage，则按该 Mission Slice 触发。

**不触发 Stage Gate 的技能（工具型）：**
执行日志、git-workflow（start-stage / commit-artifact / recover / close 操作）、Harness 自检、generate-context、e2e-setup、Stage Gate 自身、skill-router、中途纠偏、writing-plans、parallel-agents、systematic-debugging、receiving-review、verification-before-completion、ui-ux-pro-max

> 工具型技能执行完成后直接返回调用方，不启动 Gate 检查。

Stage Gate 会返回以下结论之一：

Stage Gate 必须先消费 `check_contracts.py` 的 programmatic result，再做 AI interpretation。程序化 FAIL 不能被 AI 覆盖；只能修复、回退、升级到 Decision Gate，或记录用户接受的风险。

### 可以继续
- 所有检查 PASS（或只有 WARN）
- → 调用 `git-workflow commit-artifact(<control_plane.stage>)`，提交当前 stage worktree 并合并回 mission branch
- → **立即**回到步骤 2，由 Board / Mission Slice 选择下一项 graph action。不要停下来用固定阶段链口径预告并等待确认，直接执行。

### 不能继续
- 存在 FAIL 项
- → 自行修复 FAIL 项后重新运行 Stage Gate
- → 修复 3 次仍失败 → 发起 Decision Gate

### 需要人确认（Checkpoint）
- 当前完成的 `lane_action.output_artifact` / `control_plane.stage` 命中 mission-contract 的 `required_checkpoints`；若 mission 未声明，则按 `execution_governance.levels.<autonomy_level>.human_checkpoints` 判断。旧 `A1` / `A2` / `A3` 只能通过 `legacy_level_aliases` 归一化，不读取旧 Checkpoint 配置。
- `acceptance-result` 为最终验收 Checkpoint：默认必须暂停；没有用户接受记录时不得把任务置为完成
- → 暂停，向用户展示文档，请求确认
- → 用户确认后，通过 `harness-cli` 记录 approval
- → 调用 `git-workflow commit-artifact(<control_plane.stage>)`，提交当前 stage worktree 并合并回 mission branch
- → 继续

### 升级（Escalation）
- 执行过程中发现命中了 `escalation_rules` 中的条件
- → 暂停，向用户发起决策请求（走 decision-system 规则）
- → 用户拍板后，通过 `harness-cli` 记录 approval，按决定继续

## 回退

review 发现完备性缺口时，**必须按 reviewer 在 `blocking_gap` 上标注的归因（`gap_root`）分流**，不靠主 Agent 临场判断：

- **`gap_root=self`** → 走当前阶段修复循环（见 Step 3d 的「审查未通过」），缺口由当前阶段自行补齐，不回退。
- **`gap_root=upstream`**（reviewer 同时标 `upstream_stage=X`，只标最近一级，级联收敛）→ **由控制面自动消费该信号执行回退，不靠主 Agent 自觉、不靠 prose**：reviewer verdict 的 `upstream_stage` 经 board-router 的 gate-block 出口自动装配出 `reset_mission_stage --output-node-policy keep` operation，回退到 `X`，再由 Board Router 按序重推。该机器路径已实现，主 Agent 不得手动改写或绕过。
- **`gap_root=clarification`**（根因是"输入类材料从未提供该事实"，任何 agent 重导都补不出）→ **不 reset、不本阶段自补**：board-router 的 gate-block 出口先于 upstream 回退检测此信号（`reviewer_clarification_signal`），把同批澄清需求汇总成澄清批次暂停（`pause_clarification_gate`）。主 Agent 据此**一次性**向用户澄清（`AskUserQuestion`，Capio"打包一次问"），每条答复用 `harness clarification record` 沉淀进 `materials/clarifications/`（见 `decision-system.md`「澄清答复必须沉淀回文档集」），再重推/重审自然对齐。绝不把 clarification 缺口塞进 `self` 空转，或错标 `upstream` 触发 reset 空转。

回退语义：

- **保留全部产物、不作废下游**（`--output-node-policy keep`）；重入各阶段时，execute/review 按完备/自洽重新跑，自然对齐。
- 回退全程在 `RUNTIME_ROOT/traces/` 与 `operations.log` 留痕，调度 `trace-log` 技能记录。

审批口径（消解此前「回退不需审批」与 course-correction「发起 Decision Gate」的冲突）：

- **常规 `upstream` 回退自动执行**，不暂停，仅以 `operations.log` 审计。
- **仅当回退跨越已审批 checkpoint 时，自动降级为 Decision Gate**：暂停并向用户发起决策请求（走 decision-system 规则），用户拍板后通过 `harness-cli` 记录 approval 再继续。
