# HarnessV2 按需导航索引

本文是 HarnessV2 的完整导航参考，供需要阶段、技能、Agent 或 runtime 路径全貌时按需读取。启动入口是根 `AGENTS.md`；不要把本文作为会话启动时的默认全文上下文。

## 入口与约定

| 主题 | 路径 |
|------|------|
| 轻量启动入口 | `AGENTS.md` |
| Codex 约定 | `.harness/docs/codex-conventions.md` |
| 安装 / 更新 / 迁移指南 | `INSTALL.md`（HarnessV2 源码仓库根目录） |
| Cursor 约定 | `.harness/docs/cursor-conventions.md` |
| 术语口径 | `.harness/docs/terminology.md` |
| 交互原型设计标准 | `.harness/docs/prototype-standard.md` |
| Workflow 作者约定 | `.harness/docs/workflow-authoring.md` |
| 可视化工作流 | `.harness/workflow-map.html` |

源码仓库中的 `.harness/common/...` 安装后会改写为 `.harness/common/...`；`.harness/docs/...` 安装后会改写为 `.harness/docs/...`；`harness-runtime/...` 安装后会改写为 `harness-runtime/...`。

## 规则索引

| 规则 | 权威正文 | 职责 |
|------|----------|------|
| 核心规则 | `.harness/common/rules/core.md` | 工作模式、架构、文件约定、启动流程 |
| 自治循环 | `.harness/common/rules/autonomy-loop.md` | 主执行循环、技能调度映射 |
| 产物 Gate | `.harness/common/rules/artifact-gate.md` | 阶段产物结构与 Gate 约束 |
| 决策系统 | `.harness/common/rules/decision-system.md` | Decision Gate 和 Checkpoint 机制 |
| 阶段文档标准 | `.harness/common/rules/stage-doc-standard.md` | 阶段文档写作规范 |
| 任务追踪 | `.harness/common/rules/mission-tracking.md` | 当前 Mission 状态管理 |
| 项目上下文 | `.harness/common/rules/project-context.md` | `project-context.md` 读写 |

## 阶段索引

| 阶段 | 技能 | 主要子 Agent / 审查者 | 产出 |
|------|------|------------------------|------|
| 路由 | `skill-router` | - | 技能匹配决策 |
| 项目上下文 | `generate-context` | - | `project-context.md` |
| 接入前脑暴 | `brainstorm`（可选前置） | 可选调研子 Agent（`discovery-analyst` / `Explore` / `deep-research`） | `harness-runtime/harness/brainstorms/<slug>.md`（脑暴活文档；无治理，不建 Mission / 不写控制面） |
| 任务接入 | `intake` | `mission-framing-expert` + `mission-contract-effectiveness-reviewer` | `mission-contract.md` |
| 前置分析 | `discovery` | `discovery-analyst` | `discovery-brief.md` |
| 产品定义 | `prd` | `business-domain-modeler` / `acceptance-scenario-designer` / `product-scope-strategist` → `senior-product-expert` + `product-definition-reviewer` | `product/product-definition.md` + `product/product-domain-model.md` + `product/product-evidence.md` + 差量规格 |
| 方案设计 | `design` | `solution-architect` / `tech-designer` + 对应 reviewer；按需 Agent 能力与交互角色 | `solution.md` + `tech-design.md` |
| 依赖影响证据 | `dependency-impact` | `integration-impact-expert` + `dependency-validity-reviewer` | `dependency-impact.md` |
| 任务拆解 | `breakdown` | `delivery-slicer` / `test-planning-expert` + `execution-plan-effectiveness-reviewer` | `execution-brief.md` |
| Git 准备 | `git-workflow` | - | mission branch / stage worktree |
| 实现 | `execute` | frontend / backend / client / security / integration / data / debugging / refactoring / test / general 工程角色 + `spec-reviewer`；内部使用 `execute/dispatch-plan.md` 生成 dispatch plan | 代码 + 测试 |
| 调试 | `systematic-debugging` | - | 根因分析 |
| 缺陷修复 | `bug-fix` | debugging / reviewer 按需 | 复现 + 根因 + 回归 |
| 代码评审 | `code-review` | `correctness-reviewer` + `tdd-reviewer`；按需 security / architecture / agent / e2e reviewer | `code-review.md` |
| 验证 | `verify` | `verification-engineer` + `verification-effectiveness-reviewer` | `verification-report.md` |
| Agent 行为验证 | `agent-eval` | 被评估 Agent | `agent-eval-report.md` |
| 完成前验证 | `verification-before-completion` | - | 验证证据 |
| 质量控制 | `quality-control` | 审查子 Agent 按需 | 质量分类 + 修复闭环 |
| 接收审查反馈 | `receiving-review` | - | 验证后的修复 |
| Atomic Task 队列 | `breakdown`（写盘前可内部使用 `writing-plans`） | `execution-plan-effectiveness-reviewer` | `execution-brief.md#Execution Units` |
| 分支收尾 | `finishing-branch` | - | 合并 / PR / 保留 / 丢弃决策 |
| 交付 | `delivery` | `release-readiness-expert` + `acceptance-package-reviewer` | `acceptance-result.md` + `delivery-package.md` |
| 复盘 | `retrospective` | `planning-analyst` | `retrospective.md` |
| 执行日志 | `trace-log` | - | `trace-log.md` |
| 模板自检 | `harness-lint` | - | Lint 报告 |
| 项目约束检查 | `project-lint` | - | `project-lint-report.*` |

## 技能索引

| 分类 | 技能 |
|------|------|
| 元技能 | `skill-router` |
| 规划 | `brainstorm`（接入前可选脑暴）, `intake`, `discovery`, `prd`, `design`, `breakdown` |
| 原型 / 交互 | `interaction`（默认）、`prototype-as-frontend`（`prototype.delivery_mode=frontend_engineering` 路线，产真前端工程 + MSW + shared types draft） |
| 执行 | `git-workflow`, `execute`, `e2e-setup`, `parallel-agents`, `systematic-debugging`, `bug-fix`, `finishing-branch` |
| 审查与验证 | `code-review`, `receiving-review`, `verify`, `quality-control`, `agent-eval`, `verification-before-completion` |
| 交付与治理 | `writing-plans`, `delivery`, `course-correction`, `retrospective`, `generate-context`, `stage-gate`, `trace-log`, `harness-cli`, `harness-lint`, `project-lint`, `work-graph`, `board-router` |
| 工具集成 | `query-api-docs`, `ui-ux-pro-max`, `visual-interaction-design` |
| Graphify | `graphify-exploring`, `graphify-impact-analysis`, `graphify-cli`, `graphify-debugging`, `graphify-refactoring`, `graphify-pr-review`, `graphify-guide` |

每个技能的正文位于 `.harness/common/skills/<skill>/SKILL.md`；若存在 `workflow.md`，执行阶段以 `workflow.md` 为细节依据。Graphify 技能位于 `.harness/common/skills/graphify/<skill>/`。

## 命令索引

安装后的更新 / 迁移 / 追加 adapter 走稳定命令而非自由解释 `install.py`：

| 命令 | 用途 | 资产类别 |
|---|---|---|
| `harness-upgrade` | 升级到新版本模板：可断点续跑的升级 checklist，刷新框架正文 + runtime 结构、对 `harness.yaml` 做三方迁移（保留项目设置）、按已装 adapter 重渲染、验证 + 回滚（取代旧 `harness-update` / `harness-migrate`） | A+B+C+D+E |
| `harness-add-adapter` | 已安装项目追加一个新的 adapter | B 类（adapter 入口） |

命令正文位于 `.harness/common/commands/<name>.md`（安装后位于 `.harness/common/commands/`）。各 adapter 副本由 `install.py` 渲染：原生支持的 adapter 落到 `.<adapter>/commands/`（OpenCode 是 `.opencode/command/`、Windsurf 是 `.windsurf/workflows/`）；Codex / Antigravity 通过入口文件的 reference 块查找。

## 可调用子 Agent 注册表

子 Agent role 源定义位于 `.harness/common/agents/<name>.md`。安装到目标项目时，支持原生子 Agent registry 的 adapter 必须把这些 role 物化到对应目录，例如 `.cursor/agents/<name>.md`、`.claude/agents/<name>.md`、`.opencode/agents/<name>.md`。workflow 声明调用 `<name>` 时，优先使用 adapter 原生命名子 Agent；只有当前 runtime 没有原生 registry 时，才由 workflow 按可用调度能力注入 role 正文并附加 Task Envelope。

| 子 Agent | 类型 / 默认使用场景 |
|----------|---------------------|
| `mission-framing-expert` | intake 执行 |
| `mission-contract-effectiveness-reviewer` | intake 审查 |
| `discovery-analyst` | discovery 执行 |
| `business-domain-modeler` | prd 执行（业务对象 / 领域模型分析） |
| `acceptance-scenario-designer` | prd 执行（验收场景 / GWT / 验收条件） |
| `product-scope-strategist` | prd 执行（范围策略 / 边界取舍） |
| `senior-product-expert` | prd 综合执行（产品定义包） |
| `product-definition-reviewer` | prd 审查（产品定义包） |
| `solution-architect` | design / solution 执行 |
| `tech-designer` | design / tech-design 执行 |
| `solution-effectiveness-reviewer` | solution 审查 |
| `technical-design-effectiveness-reviewer` | tech-design 审查 |
| `agent-capability-designer` | agent capability 条件执行 |
| `agent-capability-reviewer` | agent capability 条件审查 |
| `interaction-designer` | frontend / user journey 条件执行（interactive_prototype 路线） |
| `interaction-reviewer` | interaction 条件审查（interactive_prototype 路线） |
| `frontend-reviewer` | interaction 条件审查（prototype-as-frontend 路线，六维 verdict） |
| `integration-impact-expert` | dependency-impact 执行 |
| `dependency-validity-reviewer` | dependency-impact 审查 |
| `delivery-slicer` | breakdown 执行 |
| `test-planning-expert` | breakdown 执行 |
| `execution-plan-effectiveness-reviewer` | breakdown 完整 execution-brief 审查 |
| `general-engineer` | execute 兜底执行 |
| `frontend-engineer` | execute frontend surface；interaction stage `prototype-as-frontend` 路线主执行 |
| `backend-engineer` | execute backend surface |
| `client-engineer` | execute client surface |
| `security-engineer` | execute auth / permission surface |
| `interaction-engineer` | execute UI 交互辅助 |
| `integration-engineer` | execute 集成 surface |
| `data-engineer` | execute 数据 surface |
| `test-engineer` | execute 测试辅助 |
| `debugging-expert` | execute / bug-fix 调试 |
| `refactoring-expert` | execute 重构 surface |
| `spec-reviewer` | execute SDD 审查 |
| `data-migration-reviewer` | 数据迁移条件审查 |
| `correctness-reviewer` | code-review 正确性审查 |
| `tdd-reviewer` | code-review TDD 审查 |
| `security-reviewer` | code-review 安全条件审查 |
| `architecture-reviewer` | code-review 架构条件审查 |
| `agent-behavior-reviewer` | agent 行为条件审查 |
| `e2e-reviewer` | e2e 条件审查 |
| `verification-engineer` | verify 执行 |
| `verification-effectiveness-reviewer` | verify 审查 |
| `release-readiness-expert` | delivery 执行 |
| `acceptance-package-reviewer` | delivery 审查 |
| `planning-analyst` | retrospective 分析 |

## 运行数据

| 层 | 安装后路径 | 用途 |
|----|------------|------|
| 任务 | `harness-runtime/harness/missions/` | 任务契约实例 |
| Work Graph | `harness-runtime/harness/work-graph/` | 长期工作对象 node、Board、索引、树视图与 artifact 入口 |
| 阶段产物 | `harness-runtime/harness/artifacts/<id>/` | 各阶段 accepted artifacts；长期知识不得停留在这里 |
| 阶段控制契约 | `harness-runtime/harness/stages/<id>/contracts/` | Gate / contract / reviewer 结构化控制面 |
| 差量规格 | `harness-runtime/harness/artifacts/<id>/product/specs/<capability>/spec.md` | 本次任务行为变更 |
| 状态跟踪 | `harness-runtime/harness/mission-status.yaml` | 当前 Mission Slice 状态缓存 |
| 执行日志 | `harness-runtime/harness/state/trace-log.md` | 跨会话恢复依据 |
| 审批记录 | `harness-runtime/harness/state/approvals.json` | Checkpoint / 决策记录 |
| 执行证据 | `harness-runtime/harness/traces/` | 执行和回退记录 |
| 用户验收结果 | `harness-runtime/harness/artifacts/<id>/verify/acceptance-result.md` | 面向人的交付入口 |
| 交付包 | `harness-runtime/harness/artifacts/<id>/delivery/delivery-package.md` | 内部交付归档 |
| 长期知识 | `project-knowledge/` | Mission 结束后必须沉淀的项目级知识 |
| 时间脚本 | `harness-runtime/scripts/get_time.sh` | 统一时间戳 |
| 项目上下文 | `project-context.md` | AI 可读项目约束和历史教训 |

## 行为契约层

`spec.enabled=true` 时生效：

| 路径 | 用途 |
|------|------|
| `project-knowledge/engineering/policies/stage-rules.yaml` | 项目级技术约束 + per-stage rules |
| `project-knowledge/specs/_index.md` | 所有能力规格索引 |
| `project-knowledge/specs/<capability>/spec.md` | 各能力全量行为契约 |
| `harness-runtime/harness/artifacts/<id>/product/specs/<capability>/spec.md` | 本次任务差量规格 |

规格层流程：探索识别受影响能力；PRD 产出差量规格；拆解引用 Scenario；执行以差量规格为边界；code-review 逐条核查 Scenario；任务收尾通过 `harness knowledge promote --apply` 把确认后的长期行为契约固化到 `project-knowledge/specs/`。

## 方法论参考

| 文档 | 内容 |
|------|------|
| `.harness/docs/methodology-reference.md` | 生命周期阶段与业界方法论映射 |
| `.harness/docs/methodologies/stage-element-model.md` | 各阶段共享关键要素语言 |
| `.harness/docs/tdd-toolchain.md` | TDD 工具链控制面 |
| `.harness/docs/tdd-planning-contract.md` | execution-brief / Atomic Task Queue 的 TDD 计划契约 |
| `.harness/docs/methodologies/agent-capability-engineering.md` | Agent 能力工程方法论 |
| `.harness/docs/operating-model.md` | 运行模型 |
| `.harness/docs/mission-contract.md` | 任务契约设计 |
| `.harness/docs/autonomy-loop.md` | 自治循环设计 |
| `.harness/docs/routing-precondition.md` | 路由前置设计决策（为什么按意图、且无条件先路由） |
| `.harness/docs/decision-and-checkpoint.md` | 决策与 Checkpoint |
| `.harness/docs/stage-docs-spec.md` | 阶段文档规范 |
| `.harness/docs/workflow-authoring.md` | skill workflow 写作约定 |
