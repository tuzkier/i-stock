# Prototype-as-Frontend lane action 工作流

> **方法论参考**：`.harness/docs/methodologies/prototype-as-frontend-delivery.md`。
> **设计原则**：见同目录 `SKILL.md` 的"设计原则"段（interaction stage 通用原则 + 本路线专属补充）；本 workflow 的 invariants 表是这些原则的可执行落点。

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用（默认带 `--json`、消费 typed payload）。

<workflow stage="interaction" mode="frontend_engineering" version="2">

<goal>
在 `prototype.delivery_mode=frontend_engineering` 路线下，从 PRD 阶段产出的产品定义包、DDD 领域模型、`api-contract-draft.md` 和 Mission Contract 出发，对长期前端工程做一次 surface-based patch：实现 / 修改 / 扩展真页面与真组件，让用户在浏览器跑通 PRD 列出的所有用户 path（happy / 错误 / 空态 / 权限），并落出 `lib/types/` draft 作为后续阶段 freeze 的契约草案。本阶段**不写 / 不跑 Playwright e2e**，不做 a11y 完整 audit，不做覆盖率 / lint 阈值——这些由后续 `tech-design` / `execute` / `code-review` / `verify` 承接。
</goal>

<role>
你是 interaction stage 在 frontend_engineering 路线下的前端原型交付编排者。你不写交互说明 markdown 文档，你通过 `frontend-prototype-engineer` 产出真前端代码 + MSW mock + shared types draft + frontend-changeset 记录。本阶段的核心是"用户能看见效果"——所有 path 在界面上可点可见、用户在浏览器走查通过。所有 surface / page / component / state / type 必须先从用户任务、信息架构和领域可见性决策推导，再可追溯到 AC + 领域对象。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `domain-driven` | surface / page / component / state / 用户动作必须从 PRD `product-domain-model.md` 推导；每条改动有 `domain_refs` 字段；但禁止把领域实体一对一界面化，必须先说明用户任务、信息架构和领域可见性决策 | Step 1 + reviewer `domain_coverage` 维度 |
| `information-architecture-first` | route / page / section / panel / modal / list / detail 的层级必须服务用户任务和决策顺序；不得按领域实体机械拆页面 | Step 1 + reviewer `domain_coverage` 维度 |
| `domain-visibility-decision` | 每个关键领域概念必须分类为 primary_object / supporting_context / state_indicator / action_affordance / hidden_internal，并说明展示、折叠、合并或隐藏原因 | Step 1 + reviewer `domain_coverage` 维度 |
| `surface-first-baseline` | 每条改动判断 operation；非 create 改动必须引 `baseline_ref`；不另起孤立 surface | Step 1 + reviewer `surface_baseline` 维度 |
| `traceability-to-ac` | 每条改动 `traces_to` 至少一个 PRD AC + 关联至少一个领域实体 / 动作 | Step 1 / Step 5 + reviewer `domain_coverage` 维度 |
| `state-completeness` | 每个 user path 覆盖 loading / empty / error / permission / 取消 / 重复 / 边界；例外项有说明 | Step 3 + reviewer `path_completeness` 维度 |
| `visible-copy-zh-cn` | 用户可见文字默认中文；外语例外有理由 | Step 3 + reviewer `walkthrough_ready` 维度 |
| `prd-feedback-gate` | 实施过程中若需要改 PRD / 领域 / AC / 范围，停下来发 Decision Gate；不静默修改 | Step 4a |
| `e2e-locator-ready` | 关键可交互元素 testid / aria；关键状态可观察 DOM 标记；可断言点在 changeset 列出 | Step 1 / Step 3 + reviewer `path_completeness` 维度 |
| `knowledge-promotion` | 必须标出可沉淀项（pattern / type / locator 约定）供 retrospective 评估 | Step 5 / Step 9 |
| `delivery-mode-frontend-engineering` | 仅在 `prototype.delivery_mode=frontend_engineering` 时启用；否则路由错误返回 BLOCKED 给 skill-router | Step 0 |
| `frontend-project-root-resolved` | `{frontend_project_root}` 必须由 `harness config snapshot` 的 `prototype.frontend_engineering.frontend_project_root` 解析，不得硬编码 | Step 0 |
| `frontend-changeset-required` | 本次 mission 必须产出 `frontend-changeset.md`，列出 surface 改动清单、baseline ref、traces_to AC | Step 1 / Step 5 |
| `shared-types-draft-only` | `lib/types/**` 在本阶段是 **draft**；freeze 由 `tech-design` 阶段完成；不得在本阶段以"frozen 契约"自居 | Step 2 |
| `no-e2e-in-interaction` | 本阶段不创建 Playwright spec、不跑 e2e；只做 locator / aria / 断言点准备 | Step 3 / Step 4 |
| `no-quality-gates-in-interaction` | 不在本阶段执行 lint / typecheck / coverage / a11y 阈值检查作为 gate 条件（基础 lint 错误仍要修，但不作为通过门）| Step 4 |
| `reviewer-readonly` | `frontend-reviewer` 必须在 readonly subagent 中调用 | subagent registry `readonly=true` |
| `fix-then-recheck` | 任何工程修改后必须重新让用户走查并重新过 reviewer | Step 6 / Step 7 |
| `msw-interaction-scope-only` | MSW 是本阶段的演示工具；后续阶段切真 API 后不作为契约证据；本阶段不要求"覆盖镜像后端契约"，只要求"够用户走查所有 path" | Step 2 |

</invariants>

<entry>

- Mission Slice `control_plane.stage=interaction`。
- `harness config snapshot --json` 返回 `prototype.delivery_mode=frontend_engineering`。
- 上游产物齐全：`product/product-definition.md`、`product/product-domain-model.md`、`api-contract-draft.md`、`mission-contract.md`、`contracts/prd.contract.yaml`。
- `harness interaction check-ui-trigger` 返回 `requires_interaction=true`。

</entry>

<exit>

- `{frontend_project_root}/` 已就绪：`pnpm install` 干净、`pnpm dev` 启动成功、PRD 列出的所有用户 path 都能在浏览器看到。
- `frontend-changeset.md` 完整：primary user tasks、information architecture、domain visibility decisions、本次 surface 改动清单、baseline ref、traces_to AC、E2E locator 可断言点。
- `{frontend_project_root}/lib/types/**` draft 覆盖 PRD `api-contract-draft.md` 全部 endpoint。
- `{frontend_project_root}/mocks/**` 覆盖所有 path 的 MSW handler + scenario 切换器。
- `contracts/prototype-as-frontend.contract.yaml` 已填充且 `harness contract check` PASS。
- `frontend-reviewer` 四维 verdict 全 PASS（或用户降级 approval 已记录）。
- 用户浏览器走查 checkpoint：实际跑通 PRD 列出的全部用户 path（含 happy / 错误 / 空态 / 权限），记录写入 `harness-runtime/harness/traces/{mission_id}/user-walkthrough.md`。
- `harness prototype-as-frontend gate run` 返回 `status=pass`。

</exit>

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Bash(git push --force *)` | interaction 阶段禁止 |
| deny | `Bash(git reset --hard *)` | interaction 阶段禁止 |
| deny | `Write/Edit(harness-runtime/harness/stages/*/contracts/prototype-as-frontend.contract.yaml)` | contract 必须经 harness contract init/patch |
| deny | `Write/Edit(harness-runtime/harness/stages/*/solution.md)` | lane action 单一性 |
| deny | `Write/Edit(harness-runtime/harness/stages/*/tech-design.md)` | lane action 单一性 |
| deny | `Write({frontend_project_root}/tests/e2e/**)` | e2e 在后续阶段写，本阶段禁止 |
| allow | `Write({frontend_project_root}/app/**)` | 真前端工程主产物 |
| allow | `Write({frontend_project_root}/components/**)` | 真前端工程主产物 |
| allow | `Write({frontend_project_root}/lib/**)` | shared types draft + api client |
| allow | `Write({frontend_project_root}/mocks/**)` | MSW handlers + scenarios |
| allow | `Write({frontend_project_root}/package.json)` | 前端工程必需 |
| allow | `Write({frontend_project_root}/README.md)` | 前端工程必需 |
| allow | `Write(harness-runtime/harness/stages/*/frontend-changeset.md)` | 本次 patch 的 surface 改动清单 |
| allow | `Write(harness-runtime/harness/traces/{mission_id}/user-walkthrough.md)` | 用户走查 checkpoint 记录 |
| allow | `Bash(pnpm *)` | 前端工程必需 |
| allow | `Bash(harness *)` | interaction lane CLI 必需 |

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `frontend-prototype-engineer` | spawn | 可写 `{frontend_project_root}/**`（除 `tests/e2e/**`）+ `frontend-changeset.md` | `.harness/common/agents/frontend-prototype-engineer.md` |
| `frontend-reviewer` | spawn readonly | 禁止 Edit / Write / MultiEdit / NotebookEdit / Bash（除只读 pnpm 命令） | `.harness/common/agents/frontend-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `product/product-definition.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `product/product-domain-model.md` | true | Memory |
| `api-contract-draft.md` | true | Memory |
| `mission-contract.md` | true | Intent |
| `contracts/prd.contract.yaml` | true | Memory |
| `{frontend_project_root}/` 当前状态 | true（如存在，作为 baseline） | Memory |
| `project-context.md` | conditional: brownfield | Context |
| `project-knowledge/engineering/policies/stage-rules.yaml` (interaction 段) | conditional | Memory |
| `project-knowledge/_index.md` | conditional | Memory |
| `harness.yaml` | true via `harness config snapshot` | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `frontend-project-patch` | `{frontend_project_root}/`（本次新增 / 修改 / 扩展的文件） | runnable codebase | Memory + Evidence |
| `frontend-changeset` | `harness-runtime/harness/stages/{mission_id}/frontend-changeset.md` | markdown | Memory |
| `shared-types-draft` | `{frontend_project_root}/lib/types/**` | TS source（draft） | Memory |
| `msw-handlers` | `{frontend_project_root}/mocks/**` | TS source | Memory |
| `user-walkthrough` | `harness-runtime/harness/traces/{mission_id}/user-walkthrough.md` | markdown | Evidence |
| `prototype-as-frontend-contract` | `harness-runtime/harness/stages/{mission_id}/contracts/prototype-as-frontend.contract.yaml` | contract | `harness contract check --upstream prd.contract.yaml --upstream mission-contract.contract.yaml` |

</outputs>

<steps>

<step id="step-0" n="0" goal="Stage 初始化 + delivery_mode / UI 触发判断 + frontend_project_root 解析">

- 调用 `harness mission stage start --mission <mission-id> --stage interaction --json`。
- 调用 `harness trace log-init --mission <mission-id> --stage interaction --json`。
- 调用 `harness config snapshot --json`，提取：
  - `prototype.delivery_mode`：必须是 `frontend_engineering`；否则返回路由错误给 skill-router（应该调度 `interaction` skill）。
  - `prototype.frontend_engineering.frontend_project_root`：作为 `{frontend_project_root}` 占位符的解析值；未配置则回落到 `apps/web`。
  - `prototype.frontend_engineering.api_contract_draft_required`：若为 true 但上游缺 `api-contract-draft.md`，返回 BLOCKED 路由回 prd。
- 调用 `harness context check --json`；PASS 则读 `project-context.md`。
- 调用 `harness interaction check-ui-trigger --mission <mission-id> --json`。
- 调用 `harness frame current --mission <mission-id> --json`，校验 `mission_slice.control_plane.stage=interaction` 且 `lane_action.skill=prototype-as-frontend`。
- 若 `project-knowledge/engineering/policies/stage-rules.yaml` 存在 `interaction:` 段，读取其前端栈固化项作为本次实施基线；缺失时使用方法论 §3 默认值（Next.js 14 / TS strict / shadcn / Tailwind / React Query / MSW v2 / Playwright / react-hook-form + zod）。

</step>

<step id="step-1" n="1" goal="frontend-prototype-engineer 调度 + 用户任务 / 信息架构 + Surface baseline 判断 + frontend-changeset.md 起草">

通过 `Task(subagent_type="frontend-prototype-engineer", prompt=<Task Envelope>)` 工具调用 `frontend-prototype-engineer` subagent

Task Envelope 必须包含：

- 任务目标：对长期前端工程 `{frontend_project_root}/` 做本次 mission 的 surface patch，让 PRD 列出的所有用户 path 在浏览器可见可点；产出 `frontend-changeset.md` 记录本次改动。
- 输入路径和已读摘要：`product-definition.md`、`product-domain-model.md`、`api-contract-draft.md`、`mission-contract.md`、`prd.contract.yaml`、`project-context.md`（如有）、`project-knowledge/engineering/policies/stage-rules.yaml`（interaction 段）、`{frontend_project_root}/` 当前状态。
- 输出路径：`{frontend_project_root}/**`（除 `tests/e2e/**`）+ `harness-runtime/harness/stages/{mission_id}/frontend-changeset.md`。
- 设计原则 reference：本 skill `SKILL.md` 的"设计原则"段（领域驱动 / surface 优先 / 可追溯 / 状态完整 / 中文文案 / PRD 回流 / e2e locator / 长期沉淀）。
- 完成条件（本步只起草）：
  - 从 PRD path、AC、角色、权限、领域命令中识别 `primary_user_tasks`、decision moments、failure moments
  - 推导 `information_architecture`：route / page / section / panel / modal / drawer / list / detail 的层级和导航关系
  - 完成 `domain_visibility_decisions`：关键领域概念分类为 `primary_object` / `supporting_context` / `state_indicator` / `action_affordance` / `hidden_internal`，并说明展示、折叠、合并或隐藏原因
  - Surface baseline 判断完成：对 `{frontend_project_root}/app/` / `components/domain/` / `lib/types/` 现有内容做盘点
  - `frontend-changeset.md` 起草：先记录 `primary_user_tasks`、`information_architecture`、`navigation_model`、`domain_visibility_decisions`、`surface_model`、`state_action_matrix`，再列出本次 surface 改动清单（每条 `{surface_id, kind: route/page/component/type, operation: create/modify/extend/retire, file_path, baseline_ref, traces_to: [AC], domain_refs: [entity/state/action]}`）
  - 每条改动指出承载哪个用户任务、领域实体 / 状态 / 动作，以及该领域概念为什么应该可见
  - 每条改动指出对应 PRD AC

frontend-prototype-engineer 必须完成：

- 在写组件和 mock 前先完成用户任务、信息架构、导航模型和领域可见性决策；不得先把领域对象铺成页面再补解释。
- 不得把领域实体一对一做成页面、表格、卡片或表单；任何可见对象都必须说明它服务的用户任务、决策点或反馈路径。
- 对领域模型中的关键概念必须明确分类：`primary_object` / `supporting_context` / `state_indicator` / `action_affordance` / `hidden_internal`。
- 判断本次 surface 操作类型组合：`create_surface` / `modify_surface` / `extend_surface` / `retire_surface`（invariant `surface-first-baseline`）。
- 修改既有 surface 必须引用既有路由 / 组件 / 类型作为 baseline；不得生成孤立新 surface。
- 每个改动必须能映射到 domain model 的实体 / 状态 / 动作（invariant `domain-driven`）。
- 每个改动必须 `traces_to` 至少一个 AC（invariant `traceability-to-ac`）。
- changeset 中列出每个用户 path 的"可被 e2e 断言点"（locator / role + accessible name / 可观察 DOM 标记），但不写 spec（invariant `e2e-locator-ready`）。

</step>

<step id="step-2" n="2" goal="shared types draft + api client + MSW handlers + scenarios">

由 frontend-prototype-engineer 继续：

- `{frontend_project_root}/lib/types/`：从 `api-contract-draft.md` 抽出所有 endpoint 的 Request / Response 类型 + 领域实体 / 状态 enum / 值对象 + 错误类型。
  - **本阶段是 draft**，允许后续 tech-design 阶段反馈调整；不在本阶段以"frozen 契约"自居。
- `{frontend_project_root}/lib/api/`：fetch 包装层。业务代码只调这里；mock 与真后端切换由本层封装，业务代码不感知。
- `{frontend_project_root}/mocks/handlers/`：每个 endpoint 一个 handler，响应类型 import 自 `lib/types/`；不得用 any。
- `{frontend_project_root}/mocks/fixtures/`：可重用测试数据。
- `{frontend_project_root}/mocks/scenarios/`：演示分支切换器，**必须覆盖所有 path**（happy / 错误 / 空态 / 权限 / 边界），UI 在 dev / preview env 暴露切换控件。
- 业务代码（`mocks/` 之外）禁止出现 `if (process.env.NEXT_PUBLIC_MOCK)` 之类条件分支。
- **本阶段不要求 MSW 镜像真后端契约**——MSW 只是本阶段的演示工具；目标是"够用户走查所有 path"，不是"作为契约证据"。

</step>

<step id="step-3" n="3" goal="页面 + 组件 + 全 path 实现">

由 frontend-prototype-engineer 继续：

- 按 PRD 用户旅程实现页面（`app/<route>/page.tsx`）和组件（`components/domain/**`）。
- 状态管理用 React Query（服务端 state）；表单用 react-hook-form + zod；UI 用 shadcn/ui。
- **必须覆盖所有 path**（invariant `state-completeness`）：加载、空态、错误（网络 / 业务 / 校验 / 服务不可用）、权限不足、重复提交、取消、返回、刷新。
- 主流程页面必须有 ErrorBoundary + Suspense；不接受白屏 / unhandled rejection。
- 所有用户可见文字默认中文；外语例外必须在 changeset / README 标注理由（invariant `visible-copy-zh-cn`）。
- 关键可交互元素必须有 `data-testid` 或语义化 ARIA role + accessible name；关键状态有可观察 DOM 标记（invariant `e2e-locator-ready`）。
- **不写 Playwright spec / 不在 `tests/e2e/` 创建文件**——本阶段权限已 deny。
- **不要求 a11y 评分达标 / 不要求 coverage 达项目阈值**——这些由 code-review / verify 承接。

</step>

<step id="step-4" n="4" goal="基本健康检查（非 gate）">

由 frontend-prototype-engineer 继续：

- 跑基础健康检查（保证用户能走查）：
  - `pnpm install` → `harness-runtime/harness/traces/{mission_id}/install.log`
  - `pnpm dev` 启动成功，主路径返回 200 → `traces/{mission_id}/dev-startup.log`
  - 关键编译错误必须修复（不允许"以后再说"）
- **不在本阶段强制**：完整 lint 阈值、完整 typecheck 阈值、coverage、Playwright e2e、axe-core a11y 评分。基础 TS / build 错误必须修，质量门由 code-review / verify 承接。

</step>

<step id="step-4a" n="4a" goal="PRD 回流检查">

- 对照 `product-definition.md`、`product-domain-model.md`、`prd.contract.yaml`，检查实施是否引入新的用户目标、AC、Scenario、领域实体、实体状态、用户动作、权限规则或范围变化（invariant `prd-feedback-gate`）。
- 若只是把既有 PRD 内容表达为界面和状态，进入 contract 写入。
- 若需要改变 PRD 内容，停止推进，将差异写入 `frontend-changeset.md` 的「PRD 回流检查」段和 contract 的 `prd_feedback` 段，发起 Decision Gate 或路由回 prd。
- 不得直接修改产品定义包或差量 spec。

</step>

<step id="step-5" n="5" goal="contract.yaml 初始化 + execution_result 写入">

- 若 `contracts/prototype-as-frontend.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage interaction --template prototype-as-frontend --json`。
- 调用 `harness contract add-execution-result --mission <mission-id> --stage interaction --role frontend-prototype-engineer --json`。
- 调用 `harness contract patch`，把以下字段从 `frontend-changeset.md` 和工程实际形态抽取写入 contract.yaml：
  - `frontend_project.root` = 实际 `{frontend_project_root}`
  - `frontend_changeset.primary_user_tasks[]` = changeset 中的 primary user tasks
  - `frontend_changeset.information_architecture` = changeset 中的 route / page / section / navigation / decision order
  - `frontend_changeset.domain_visibility_decisions[]` = changeset 中的 primary_object / supporting_context / state_indicator / action_affordance / hidden_internal 分类与理由
  - `frontend_changeset.surface_model[]` = changeset 中的 surface model
  - `frontend_changeset.state_action_matrix[]` = changeset 中的 state / action / observable feedback 映射
  - `frontend_changeset.surfaces[]` = changeset 全量
  - `api_contract_draft.endpoints[]` = 从 `lib/types/` 与 `api-contract-draft.md` 比对生成
  - `msw_coverage.scenarios[]` = 从 `mocks/scenarios/` 抽取
  - `e2e_locator_obligations[]` = 每个 user path 的可断言点（给后续 tech-design / execute 用）
  - `obligations[].traces_to.ac` 命中 PRD AC
  - `knowledge_promotion_candidates[]` 列出可沉淀项
- 调用 `harness contract check --artifact contracts/prototype-as-frontend.contract.yaml --upstream prd.contract.yaml --upstream mission-contract.contract.yaml --json`；FAIL 必须修复。

</step>

<step id="step-6" n="6" goal="frontend-reviewer 循环（四维 verdict）">

最多 3 轮；本轮 `frontend-reviewer` 返回整体 PASS 时退出。

通过 `Task(subagent_type="frontend-reviewer", prompt=<Task Envelope>)` 工具调用 `frontend-reviewer` subagent

Reviewer brief 必须包含：

- `{frontend_project_root}` 路径 + `frontend-changeset.md` + PRD 包 + `api-contract-draft.md` + `contracts/prototype-as-frontend.contract.yaml`。
- 设计原则 reference：本 skill `SKILL.md` 的"设计原则"段（reviewer 评审依据）。
- 四维 verdict 要求：**domain_coverage**（用户任务 + 信息架构 + 领域可见性 + 可追溯，且没有领域模型一对一机械界面化）、**surface_baseline**（surface 优先 + baseline + changeset）、**path_completeness**（状态完整 + e2e locator 就位 + MSW 覆盖所有 path）、**walkthrough_ready**（用户能在浏览器点遍 + 中文文案 + `lib/types/` draft 覆盖 + scenario 切换器可用）；任一未 PASS 整体不 PASS。
- 明确告知 reviewer：本阶段**不评 e2e 充分性 / a11y 评分 / coverage / lint 阈值**，这些是 code-review / verify 的事；本阶段评的是"效果到位 + 共性约束遵守"。

每轮进入前调用：

```bash
harness contract patch --add-round --mission <mission-id> --stage interaction --review effectiveness --json
```

处理审查结论：

- HOLD / BLOCKED：按缺口修复 changeset / 工程代码 / MSW / lib/types draft，重启 dev 验证主路径，再重入 reviewer。
- PASS：调用 `harness contract patch --reviewer-verdict PASS --mission <mission-id> --stage interaction --json`，退出循环。
- 达到 3 轮仍有阻断：询问用户选择解决方向、接受降级 approval，或升级 BLOCKED。

</step>

<step id="step-7" n="7" goal="用户浏览器走查 checkpoint">

- 启动 `pnpm dev`，把 URL 给用户。
- 由用户在浏览器实际操作前端，跑通 PRD 列出的全部用户 path（happy / 错误 / 空态 / 权限），通过 scenario 切换器观察各分支。
- 主流程把走查结果写入 `harness-runtime/harness/traces/{mission_id}/user-walkthrough.md`，含：
  - 每个 path × 每个 AC 的 PASS / FAIL + 用户文字反馈
  - 演示分支切换是否符合预期
  - 用户可见文案是否准确（中文 / 例外）
  - 用户对继续推进的明确意见
- 若用户走查 FAIL：按反馈回 Step 3 修复，重新进入 reviewer 循环。
- 若用户走查 PASS：调用 `harness approval append --mission <mission-id> --type acceptance_checkpoint --stage interaction --status approved --json`。

</step>

<step id="step-8" n="8" goal="Artifact Gate 自检">

- 调用 `harness contract check --artifact contracts/prototype-as-frontend.contract.yaml --upstream prd.contract.yaml --upstream mission-contract.contract.yaml --json`。
- 调用 `harness prototype-as-frontend changeset-check --mission <mission-id> --json`：校验 `frontend-changeset.md` 先有 primary user tasks + information architecture + domain visibility decisions，再校验每条改动都有 baseline ref（如非 create）+ traces_to + domain_refs。
- 调用 `harness prototype-as-frontend path-check --mission <mission-id> --json`：校验每个 user path 都有界面实现 + MSW handler / scenario + locator 标记。
- 调用 `harness alignment check --mission <mission-id> --stage interaction --json`：验证 surface / page / state 对齐 PRD + domain model。
- 调用 `harness prototype-as-frontend gate run --mission <mission-id> --json`：聚合上述检查 + reviewer verdict + user walkthrough approval。

</step>

<step id="step-9" n="9" goal="Stage 完成 + Work Graph 输出">

- 调用 `harness mission stage complete interaction --mission <mission-id> --json`。
- `lane_action.output_artifact` = `{frontend_project_root}/`（本次 patch 的产物视为对长期前端工程的增量）；supplementary_artifacts 包含 `frontend-changeset.md` + shared types draft + mocks + user-walkthrough。
- 在 contract YAML 的 `work_graph_artifact` 段引用同一组路径。
- `knowledge_promotion_candidates` 段记录可沉淀的前端模式、组件、shared types pattern、MSW pattern、locator 约定；retrospective 时由 planning-analyst 评估是否进入 project-knowledge。
- 提示后续 stage：本 stage 不交付 e2e / coverage / a11y 评分；`tech-design` 需要 freeze shared types 并产 e2e test plan，`execute` 实现 e2e + 联调 + 测试加固，`code-review` 做完整 a11y / lint / coverage audit，`verify` 跑真后端 e2e。

</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `delivery-mode-mismatch` | Step 0 发现 `prototype.delivery_mode` 不是 `frontend_engineering` | 返回 BLOCKED 给 skill-router，请求路由到 `interaction` skill |
| `frontend-project-root-unresolved` | Step 0 无法从 config 解析 `frontend_project_root` 且 fallback 也不可用 | 发起 Decision Gate 让用户指定路径 |
| `api-contract-draft-missing` | Step 0 上游缺 `api-contract-draft.md` 且 `api_contract_draft_required=true` | 返回 BLOCKED，路由回 prd 补齐 |
| `pnpm-install-fail` | Step 1 install 失败 | 检查 node 版本 / pnpm 配置 / 依赖冲突；不能跳 |
| `pnpm-dev-fail` | Step 4 dev 启动失败或主路径 5xx / 白屏 | 修复后才能继续 |
| `surface-baseline-missing` | Step 1 / Step 8 changeset 缺 baseline ref（非 create operation） | 回 Step 1 引用既有 surface 或重新判断 operation 类型 |
| `traceability-incomplete` | Step 5 / Step 8 缺 primary user tasks / information architecture / domain visibility decisions，或改动缺 traces_to AC / domain_refs | 回 Step 1 补齐；可能触发 PRD 回流 |
| `path-incomplete` | Step 8 user path 缺界面 / MSW / scenario / locator | 回 Step 2 / Step 3 补齐 |
| `prd-feedback-required` | Step 4a 发现实施需要改变 PRD / 领域模型 / AC / 范围 | 停止推进，记录差异，发起 Decision Gate 或路由回 prd |
| `frontend-reviewer-blocked` | Step 6 返回 BLOCKED | 按缺口修复重启 dev，回 reviewer |
| `reviewer-max-rounds` | Step 6 达到 max rounds | 进入用户 checkpoint |
| `user-walkthrough-fail` | Step 7 用户走查 FAIL | 按反馈回 Step 3，不得跳过 |
| `gate-fail` | Step 8 `harness prototype-as-frontend gate run` FAIL | 按 failed_checks 回 Step 3 / Step 5 修复 |

</failure_paths>

</workflow>
