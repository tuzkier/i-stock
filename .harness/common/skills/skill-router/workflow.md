# 技能 Router 工作流

**Goal:** 在每轮消息开始时把用户意图、当前 Mission Slice 和控制面状态路由到正确 skill 组合。

**Your Role:** 你是技能调度器。你只做路由判断和调用顺序编排，不替代被路由 skill 的执行内容。

---

<workflow skill="skill-router" version="2">

<step n="1" goal="消息分析">
 - 收到用户消息后，立即提取关键信号：
 - 是否包含任务关键词（开始/新建/做/实现/修复/优化/重构）
 - 是否包含 Skill 触发词（调试/验证/审查/提交/设计/分析）
 - 是否包含状态信号（失败/报错/不工作/完成/搞定）
 - `harness-cli` 提供的当前 Mission / Mission Slice `lane`、`stage`、从 `lane_action.skill` 派生的 dispatch skill。没有 Mission Slice 但 Mission 仍 active 时直接 BLOCK 并要求 `board-router` 重建 slice，不再从 `mission_status.current_stage` 派生控制面。
 - 对 `continue`、`new_task`、`status`、`review`、`verify`、`bug_report` 场景，先叠加 CLI-first control-plane preflight：`harness control status --json`、`harness control candidates --intent continue --json`；显式确定 mission 后再执行 `harness control frame --mission <mission-id> --json`、`harness control guidance --mission <mission-id> --json`、`harness control context-index --mission <mission-id> --json`。
 - `harness control candidates` 只提供候选和排序原因；不得把 candidates 当作最终选择。
 - 如果 control 查询不可用而临时读取旧 runtime 文件，必须把 `fallback_used`、`fallback_reason`、`legacy_source`、`follow_up` 写入本轮路由记录或阶段产物。
</step>

<step n="2" goal="按优先级匹配技能">
 - 优先级顺序和信号匹配逻辑见 `SKILL.md` DOT 决策图和技能优先级表，不在此重复。
 - 按 DOT 决策图和 SKILL.md 优先级表，从上到下依次检查是否有信号命中。
</step>

<step n="2a" goal="新任务的 brainstorm 前置分叉">
 - 条件：命中"新任务 / 新需求"且尚未进入正式接入
  - 判断需求成色：需求是想法 / 方向 / 痛点且"具体要做成什么样"还没想透，或用户显式说"先脑暴 / 先讨论想透 / 帮我把需求想清楚 / 先别急着开干" → 调度 `brainstorm`（接入前想透"要什么"），收敛后由 `brainstorm` 交棒 `intake`。
  - 需求已是清晰外部结果且带执行确认 → 跳过 brainstorm，直接调度 `intake`。
  - 拿不准时调度 `brainstorm`，由它 step-0 用一句话向用户确认"先想透还是直接开始"，不在路由层硬判。
  - `brainstorm` 是可选前置，不建 Mission / 不签契约 / 不写控制面；不替代 `intake`，收敛物只作为 `intake` 输入。
</step>

<step n="3" goal="处理 execute 精确匹配">
 - 条件：当前 Mission Slice / Work Graph lane action 的 control_plane.stage=execute，或 lane_action.skill=execute
  - 调度 `execute`，读取 `execute/SKILL.md` 和 `workflow.md`。
  - 不得把该场景按普通状态同步、trace 修复、Work Graph 对齐或主 Agent 直接编码处理。
</step>

<step n="3a" goal="处理 interaction stage 双路线分派">
 - 条件：当前 Mission Slice control_plane.stage=interaction（即原型阶段）
  - 调用 `harness config snapshot --json`，读取 `prototype.delivery_mode`。
  - delivery_mode=interactive_prototype（默认）→ 调度 `interaction` skill（HTML 变体 + interaction-spec + visual-interaction manifest 路线）。
  - delivery_mode=frontend_engineering → 调度 `prototype-as-frontend` skill（先产 `interaction-spec/`，再产真前端工程 + MSW + shared types draft 路线，详见 docs/methodologies/prototype-as-frontend-delivery.md）。
  - 两条路线互斥；同一 mission 不得同时调度两个 skill。
  - 若 lane_action.skill 已显式指定，优先按它分派；指定值与 delivery_mode 冲突时停下来报告冲突，请求用户确认。
</step>

<step n="4" goal="叠加 Graphify 代码库分析技能">
 - 条件：用户消息或当前阶段包含：项目分析 / 代码库分析 / 架构理解 / 现有代码 / 调用链 / 执行流
  - 若是新 Mission 或复杂度 >= medium，主流程仍调度 discovery。
  - 同时将 `graphify-exploring` 作为 discovery 的辅助 skill 载入，用于代码库全貌、模块聚类和执行流分析。
 - 条件：用户消息或当前阶段包含：影响分析 / blast radius / 会不会影响 / 谁依赖它 / 安全改动评估
  - 调度 `graphify-impact-analysis`；若当前处于 discovery 已明确设计路线/关键假设后，或 dependency-impact evidence carrier / registered action 内，则作为该 Mission Slice 的第三层代码影响分析证据。
 - Graphify 辅助技能不替代阶段技能或 evidence carrier：`discovery` 仍负责产出 `discovery-brief.md`，`dependency-impact` 仍负责产出 `dependency-impact.md` 并绑定当前 Mission Slice；Graphify 只提供证据和执行流/影响链。
</step>

<step n="5" goal="叠加 Harness CLI 控制面技能">
 - 条件：用户消息或当前阶段 workflow 需要调用 `harness ...`，或需要读取/修改 CLI 支持的 Harness 控制面文件，或需要通过 CLI 处理 Gate / Board / Work Graph / Contract / Evidence / Lint / Mission / Approval / Frame
  - 调度 `harness-cli` 解析 root、选择可执行入口并运行命令。
  - 不得由调用方直接读取/写入 CLI 可管理的 YAML / JSON，也不得直接拼接底层 scripts 路径。
 - `harness-cli` 是工具型 skill，不替代阶段技能：`stage-gate`、`board-router`、`work-graph`、`verify`、`project-lint` 等仍负责业务语义和阶段产物，`harness-cli` 只负责 CLI 命令入口、执行和结构化结果处理。
</step>

<step n="6" goal="宣布并调用">
 - 按 `SKILL.md` 中的宣布格式说明正在使用的 Skill。
 - 调用该 Skill，严格遵循其 workflow。
</step>

<step n="7" goal="多技能叠加顺序">
 - 多个技能同时适用时，按治理层（intake/stage-gate）→ 流程层（discovery/debugging）→ 执行层（execute/git-workflow）的顺序推进。
</step>

<step n="8" goal="无匹配处理">
 - 条件：确认无技能适用
  - 检查 `autonomy-loop` 的当前阶段。
  - 根据阶段状态正常响应。
  - 在执行日志中记录本轮跳过 skill-router 的原因。
</step>

</workflow>
