# 原型即前端交付（Prototype-as-Frontend Delivery）

> **日期**：2026-05-21（v1）/ 2026-05-21（v2：基于落地讨论收缩 interaction stage 职责）

---

## 1. 核心命题

`interaction` stage 的产出物从"HTML 变体 + preview + manifest"换成"可运行前端工程 patch + MSW + shared types draft"。

**关键修正（v2）**：interaction stage 不背"生产级完整代码"的包袱。前端工作要按"每个阶段证明什么"切到不同阶段：

- **interaction**：证明**效果**——用户在浏览器走查所有 path（happy / 错误 / 空态 / 权限）通过；shared types 是 draft；MSW 够走查
- **tech-design**：freeze shared types + 设计 e2e test plan
- **execute**：写 e2e spec / 单元 / 组件测试 + MSW→真 API 切换 + 联调 + 修复
- **code-review**：完整 a11y audit（含键盘焦点）+ lint / typecheck / coverage 达项目阈值
- **verify**：跑真后端 e2e + AC 验证

所有 Harness stage 顺序、lane 结构、其它 role / contract / gate 全部保持原样。

---

## 2. 流程

```
intake → discovery → prd → interaction → solution → tech-design → breakdown → execute → code-review → verify → delivery → finishing-branch
                            ▲                          ▲                      ▲           ▲           ▲
                            │                          │                      │           │           │
                  ┌─────────┴──────────┐   ┌──────────┴────────┐  ┌──────────┴──┐ ┌──────┴────┐ ┌────┴────┐
                  │ 效果：surface       │   │ shared types       │  │ e2e 实现 +  │ │ 完整 a11y │ │ 真后端  │
                  │ patch + 全 path +   │   │ freeze + e2e test  │  │ 测试加固 +  │ │ + lint + │ │ e2e +   │
                  │ MSW + types draft + │   │ plan 设计          │  │ 切真 API + │ │ coverage │ │ AC 验证 │
                  │ 用户走查（无 e2e）  │   │                    │  │ 联调 + 修复 │ │ audit    │ │         │
                  └────────────────────┘   └────────────────────┘  └────────────┘ └──────────┘ └─────────┘
```

**`interaction` 阶段的输入** —— PRD 全套：`product-definition.md` / `product-domain-model.md` / `prd.contract.yaml` / `mission-contract.md` / `api-contract-draft.md`。

**`interaction` 阶段的产出**：

| 路径 | 用途 | 备注 |
|---|---|---|
| `<frontend-project>/` | Next.js 真前端工程；本次 mission 是它的 surface patch | living codebase，不重写 |
| `<frontend-project>/lib/types/` | API shared types **draft**（覆盖 PRD `api-contract-draft.md` 全部 endpoint） | tech-design 阶段 freeze |
| `<frontend-project>/lib/api/` | API client（fetch wrappers，base URL 一改即可切真后端） | |
| `<frontend-project>/mocks/` | MSW handlers + fixtures + scenarios（覆盖所有 path）| 仅本阶段演示用，切真 API 后不作契约证据 |
| `harness-runtime/harness/stages/<mission-id>/frontend-changeset.md` | 本次 surface 改动清单（primary user tasks + information architecture + domain visibility decisions + baseline ref + traces_to + domain refs + locator obligations） | |

**`interaction` 阶段不产出**：
- `<frontend-project>/tests/e2e/` — e2e spec 在 execute 阶段写（权限 deny）
- 完整 a11y / coverage / lint 报告 — code-review 阶段做

**`interaction` 阶段的角色** —— `frontend-prototype-engineer` 实现 + `frontend-reviewer` 评审（四维 verdict：domain_coverage / surface_baseline / path_completeness / walkthrough_ready）。其中 `domain_coverage` 不只是“领域对象出现了”，还必须证明用户任务、信息架构和领域可见性决策成立，防止把领域模型机械铺成界面。

**其它 stage 的职责聚焦（v2 修正）：**
- `solution`：路线 / 决策，前端栈不在此定（项目级 config 已定），侧重后端 / 数据 / 集成
- `tech-design`：**freeze shared types**（含 Decision Gate）+ 后端模块 / 接口契约 / 数据 model + **设计 e2e test plan**（基于 interaction 阶段的 `e2e_locator_obligations[]`）
- `execute`：实现后端 + **写 Playwright e2e spec + 单元 / 组件测试** + 切 MSW → 真 API + 联调 + bug 修复；前端骨架默认不重写
- `code-review`：**完整 a11y audit（含键盘焦点）+ lint / typecheck / coverage 达项目阈值**；frontend_engineering 路线下强制启用 e2e-reviewer
- `verify`：**Playwright e2e against 真后端 PASS** + AC 验证（MSW 不参与本阶段）
- `delivery` / `finishing-branch`：照常

**用户验收 checkpoint：** 用户在浏览器走查 PRD 列出的全部用户 path（happy / 错误 / 空态 / 权限），通过 scenario 切换器观察各分支，PASS。

### 2.1 `interaction` stage 输入 / 产出对照

**两边共同的输入（不变）：**
- PRD 全套：`product-definition.md` / `product-domain-model.md` / `prd.contract.yaml` / `mission-contract.md` / `api-contract-draft.md`
- 项目级前端规范：组件库 / 视觉规范 / 主题（写在 `project-knowledge/engineering/policies/stage-rules.yaml` 的 `interaction` 段）
- 项目级前端栈（仅"原型即前端交付"额外消费 mock / e2e / state 库等运行时部分；两边共用同一份组件库与视觉规范）

**真正的差异：**

| | 单独原型 | 原型即前端交付（v2） |
|---|---|---|
| 阶段内中间产物形态 | markdown 文档形态的 spec | spec-as-code（TS draft 类型 + mock + frontend-changeset） |
| 中间产物是否可执行 | 否（纯文档） | 部分（types 编译、handlers 真跑；e2e 不在本阶段） |
| 核心产出 | 高保真可交互原型（HTML / 原型工具） + preview | 可运行前端工程 patch（真页面 + 真组件 + MSW 覆盖所有 path + `lib/types/` draft）|
| 评审方式 | reviewer 看 spec + variant 文字 | reviewer 在浏览器点真交互 + 看代码 + 看 changeset（不评 e2e / a11y 评分 / coverage） |
| 用户验收 | 直接操作高保真原型 + 配合页面说明文案理解状态流转 | 在浏览器实际操作真前端，scenario 切换器走遍所有 path |
| 代码命运 | 扔（execute 阶段从零重写） | 直接被后续阶段沿用：tech-design freeze types、execute 写 e2e + 联调、code-review 做质量门、verify 跑真后端 e2e |
| 重复劳动 | 高（前端在 execute 阶段重新写一遍） | 无（前端骨架已就绪，后续阶段补质量门 + e2e + 联调） |

---

## 3. 技术栈

| 层 | 选型 |
|---|---|
| 框架 | Next.js 14 App Router |
| 类型 | TypeScript strict |
| 组件库 | shadcn/ui（Radix + Tailwind） |
| 状态管理 | React Query / SWR（服务端 state）+ 局部 state 按项目自决 |
| 路由 | Next App Router + middleware（鉴权 / 重定向） |
| Mock backend | MSW v2（**仅 interaction 阶段演示用**；切真 API 后保留作离线开发，不作契约证据） |
| API contract（draft） | TypeScript shared types（**interaction 阶段 draft；tech-design 阶段 freeze**） |
| 表单 | React Hook Form + Zod |
| 测试 | Playwright（e2e，**execute 阶段写**）+ Vitest（unit，**execute 阶段写**）+ Testing Library（component） |
| i18n | next-intl |
| 错误监控 | Sentry SDK |

项目级 config（`project-knowledge/engineering/policies/stage-rules.yaml`）固化以上栈，所有 mission 沿用。如某 mission 需要换栈，由 `solution` stage 发起 Decision Gate 决策，结论回写项目 config。

---

## 4. 目录结构

```
<frontend-project>/
├── app/              # 路由
├── components/
│   ├── ui/           # 原始组件（shadcn）
│   ├── shell/        # 导航 / 布局
│   └── domain/       # 业务组件
├── lib/
│   ├── api/          # API client
│   ├── types/        # ★ shared types：前后端契约真值
│   └── utils/        # 工具
├── mocks/            # ★ MSW handlers / fixtures / scenarios
├── tests/
│   ├── e2e/          # Playwright
│   └── components/   # Testing Library
├── docs/
│   └── API.md        # API contract
├── README.md
└── package.json
```

★ = 前后端契约真值，"接后端零改动"的关键。

---

## 5. Mock 策略

> **v2 定位修正**：MSW 是 **interaction 阶段的演示工具**，让用户走查时所有 path（happy / 错误 / 空态 / 权限 / 边界）都能在浏览器看到。execute 阶段切真 API 后，MSW **不作为契约证据**——可保留作离线开发用，也可删；不再做 mock vs real 一致性 contract test（v1 §8 中的"Mock 漂移"风险条款已删除）。

### 5.1 MSW handlers

```ts
// mocks/handlers/workspaces.ts
import { http, HttpResponse } from "msw";
import { workspacesFixture } from "../fixtures/workspaces";

export const workspaceHandlers = [
  http.get("/api/workspaces", () => HttpResponse.json(workspacesFixture)),

  http.post("/api/workspaces", async ({ request }) => {
    const body = await request.json();
    if (!body.repositoryUrl?.startsWith("git@")) {
      return HttpResponse.json({ error: "AC-12: SSH only" }, { status: 422 });
    }
    const newWs = createMockWorkspace(body);
    workspacesFixture.push(newWs);
    return HttpResponse.json(newWs, { status: 201 });
  }),
];
```

前端代码通过 `fetch("/api/workspaces")` 访问 —— 不知道是 mock 还是真后端。切真后端时前端代码不动，只换 base URL（`NEXT_PUBLIC_MOCK=false`）。

### 5.2 演示分支 scenario 切换器

```ts
// mocks/scenarios/auth-failed.ts
export function applyAuthFailedScenario(server) {
  server.use(
    http.post("/api/runs/:id/start", () => HttpResponse.json(
      { state: "Failed", end_reason: "auth_failed" },
      { status: 200 },
    )),
  );
}
```

UI 在 dev / preview env 暴露切换器：happy / cancel_unsupported / auth_failed。底层是 mock backend 行为，不是前端硬编码。

### 5.3 shared types（前端类型 + 后端实现参考契约）

> **v2 定位修正**：v1 把 shared types 叫"前后端契约真值（接后端零改动的关键）"，前提是 MSW 永久存在。v2 删除该前提后，shared types 的定位是**前端工程内部用的类型 + 后端实现的参考契约**，不是跨前后端的永久共享物。

**生命周期**：

| 阶段 | 状态 |
|---|---|
| prd | 文字草图（`api-contract-draft.md`）|
| interaction | 落成 `lib/types/**` TS 文件，**draft**（给前端 + MSW 用，允许后续调整）|
| tech-design | 后端反馈后 freeze 进契约（含 Decision Gate）|
| execute | 前端 import 用，后端按这套实现（TS / OpenAPI generator / 手工对齐皆可）|

```ts
// lib/types/agent-run.ts
export type AgentRunState =
  | "queued" | "dispatched" | "running"
  | "succeeded" | "failed" | "cancelled" | "unsupported-cancel";

export interface CapabilitySnapshot {
  cancel: "supported" | "unsupported" | "best_effort";
  resume: "supported" | "unsupported" | "best_effort";
  streaming: "supported" | "unsupported" | "best_effort";
  cost_reporting: "supported" | "unsupported" | "best_effort";
  honesty_flag: boolean;
}

export interface AgentRunResponse {
  id: string;
  mission_id: string;
  executor_type: "claude_executor" | "cursor_executor";
  state: AgentRunState;
  capability_snapshot: CapabilitySnapshot;
  end_reason: EndReason | null;
}
```

后端实现时 `import` 此 types 包。如后端是 Python/Go，用 OpenAPI generator 双向同步。

---

## 6. Harness 框架改动

### 6.1 lane / stage 配置

所有 lane 和 stage 顺序保持原样：

| lane | stages |
|---|---|
| requirement-lane | intake / discovery |
| product-definition-lane | prd / interaction（条件 `ui_task`）|
| solution-lane | solution |
| technical-analysis-lane | technical_analysis |
| breakdown-lane | breakdown |
| development-lane | execute / code-review |
| verification-lane | verify |
| delivery-lane | delivery / finishing-branch |

### 6.2 `interaction` stage 规格对照

| 项 | 单独原型 | 原型即前端交付 |
|---|---|---|
| output_artifact | `interaction.md` | `<frontend-project>/`（完整可运行前端工程） |
| supplementary_artifacts | `interaction-spec/**` + `visual-interaction/variants/**` + `preview/**` + `visual-interaction-manifest.json` | `<frontend-project>/mocks/` + `<frontend-project>/tests/e2e/` + `<frontend-project>/lib/types/` |
| required_execution_roles | `interaction-designer` | `frontend-prototype-engineer` |
| required_review_roles | `interaction-reviewer` | `frontend-reviewer` |
| contract type | `guide_contract` | `implementation_contract` |
| obligation type | `interaction` | `frontend_implementation` |

### 6.3 `interaction` stage gate（v2 收缩版）

- 前端工程能 `pnpm dev` 跑起来
- MSW 覆盖**所有 user path**（happy / 错误 / 空态 / 权限 / 边界），scenario 切换器齐全
- PRD 列出的所有用户 path 在浏览器可点可看
- 用户在浏览器实际跑通全部 path（不是看图想象）
- `lib/types/**` **draft** 覆盖 PRD `api-contract-draft.md` 全部 endpoint（不要求 freeze）
- `frontend-changeset.md` 完整：先有 `primary_user_tasks` / `information_architecture` / `navigation_model` / `domain_visibility_decisions` / `surface_model` / `state_action_matrix`，每条改动再有 `operation` / `baseline_ref`（非 create 时）/ `traces_to` AC / `domain_refs` / `e2e_locator_obligations`
- frontend-reviewer **四维 verdict** 全 PASS：domain_coverage / surface_baseline / path_completeness / walkthrough_ready

**不在 interaction stage gate**（移交下游）：

- ~~Playwright e2e 跑通~~ → execute 写 + 跑（against mock），verify 跑（against 真后端）
- ~~a11y 评分达标 / 键盘焦点 / 对比度~~ → code-review 完整 audit
- ~~lint / typecheck / coverage 达项目阈值~~ → code-review
- ~~API contract 已稳定~~ → tech-design freeze
- ~~mock 与真后端行为一致性 contract test~~ → v2 删除该约束

### 6.4 角色对照（v2）

| 单独原型 | 原型即前端交付 | 职责变化 |
|---|---|---|
| `interaction-designer` | `frontend-prototype-engineer` | 从写 interaction-spec / HTML 变体 → 先定用户任务、信息架构和领域可见性，再实现 surface patch + MSW + shared types draft + frontend-changeset |
| `interaction-reviewer` | `frontend-reviewer`（四维 verdict） | 从评 spec 文字 → 评 domain_coverage（含信息架构 / 领域可见性 / 反机械界面化）/ surface_baseline / path_completeness / walkthrough_ready；**不评 e2e / a11y 评分 / coverage / lint**（那些是 code-review 的事） |
| `visual-interaction-designer`（子流程） | ⛔ 不使用 | 不再产 HTML 变体；visual-interaction-design skill 保留给 interactive_prototype 路线用 |

**execute 阶段 `frontend-engineer`（生产实现角色）**：
- 不重写 interaction 阶段产出的前端骨架
- 按 surface 标签做事：`frontend_integration`（联调）/ `frontend_test_hardening`（写 e2e + 单元 / 组件测试）/ `frontend_bug_fix`（修联调暴露的 bug）
- 不允许出现 `frontend_ui`（新前端 UI 需求）；遇到则发 Decision Gate

**code-review 阶段额外评审维度（frontend_engineering 路线下强制）**：
- 完整 a11y audit（含键盘焦点 / 焦点可见 / aria 完整 / 对比度 / 屏幕阅读器路径）
- lint / typecheck strict / coverage 达项目阈值
- e2e-reviewer 强制启用，审 Playwright e2e spec 是否覆盖上游 `e2e_locator_obligations[]`

**verify 阶段额外**：
- Playwright e2e **against 真后端** PASS（不是 against MSW）
- 每个 user path 至少命中一个 locator obligation

其它 lane 的角色（`solution-architect` / `tech-designer` / `delivery-slicer` / `code-reviewer` / `verification-engineer` 等）完全不动；tech-designer 在 frontend_engineering 路线下额外做"freeze shared types + 设计 e2e test plan"。

### 6.5 控制契约 `interaction.contract.yaml`

```yaml
control_contract:
  type: implementation_contract
  stage: interaction
  work_graph_lane: product-definition-lane
  consumers: [solution, tech-design, breakdown, execute, verify]
  upstream:
    - product-definition.md
    - product-domain-model.md
    - prd.contract.yaml
    - mission-contract.md
    - api-contract-draft.md
  produced_artifacts:
    - path: <frontend-project>/
    - path: <frontend-project>/lib/types/
    - path: <frontend-project>/mocks/
    - path: <frontend-project>/tests/e2e/
  obligations:
    - id: OBL-INTERACTION-001
      type: frontend_implementation
      required_evidence:
        - reviewer_verdict (frontend-reviewer)
        - playwright_run_passed (happy + P0 分支)
        - msw_coverage_check (PRD 全部 API 都有 mock handler)
        - api_contract_frozen (lib/types 已稳定)
        - a11y_audit (axe-core / lighthouse 评分达标)
        - user_browser_walkthrough_passed (用户在浏览器实际跑通全部 P0 AC)
      blocking: true
  role_policy:
    required_execution_roles: [frontend-prototype-engineer]
    required_review_roles: [frontend-reviewer]
```

### 6.6 PRD 阶段产出补充

PRD stage 在原产物基础上补一份 `api-contract-draft.md` 或 `view-models.ts` 草案，给出 API 形状草图，interaction 阶段实现时固化。

### 6.7 前端栈项目级 config

`project-knowledge/engineering/policies/stage-rules.yaml` 的 `interaction` 段：

```yaml
interaction:
  framework: "next.js@14"
  state: "react-query@5"     # 领域状态机库由项目按需自选，方法论不指定
  ui: "shadcn/ui + tailwindcss@3"
  mock: "msw@2"
  e2e: "playwright"
  forms: "react-hook-form + zod"
```

interaction 阶段直接沿用，不再做技术选型。

---

## 7. 成本

### 7.1 当前 TheForce demo 升级到生产级（v2 工作量切分）

**interaction stage 内（只做"效果"层面）：**

| 工作项 | 工作量 |
|---|---|
| 把 `journey-context.tsx` 硬编码 state 换成 MSW + React Query | 1 天 |
| 新建 `lib/api/*.ts` 包装 fetch | 半天 |
| 抽出 `lib/types/` shared types **draft** | 半天 |
| MSW 覆盖所有 path（happy + 错误 + 空态 + 权限）+ scenario 切换器 | 半天 |
| 写 `frontend-changeset.md`（surface 清单 + baseline + traces + locator obligations）| 半天 |
| **interaction stage 合计** | **≈ 3 天** |

**后续阶段补质量门（不在 interaction stage 算）：**

| 工作项 | 工作量 | 阶段 |
|---|---|---|
| tech-design freeze shared types + 设计 e2e test plan | 半天 | tech-design |
| 写 Playwright e2e 覆盖全 path（含 P0 + P1 + 负路径）| 1 天 | execute |
| 加 ErrorBoundary + Suspense + 单元 / 组件测试 | 半天 | execute |
| 真后端联调 + bug 修复 | 视后端而定 | execute |
| 跑 axe-core a11y audit + 键盘焦点完整覆盖 + 对比度 | 半天 | code-review |
| lint / typecheck / coverage 达项目阈值 | 半天 | code-review |
| e2e against 真后端 PASS | 视后端而定 | verify |

### 7.2 Harness 框架升级

| 工作项 | 工作量 |
|---|---|
| 改 `interaction.contract.yaml` 模板 | 半天 |
| 改 `interaction skill workflow.md`（产真前端工程） | 1 天 |
| 删除 `visual-interaction-design` 子流程 | 半天 |
| 新增 `frontend-prototype-engineer` agent prompt，并收窄 `frontend-engineer` 为 execute 角色 | 半天 |
| 改 `interaction-reviewer` agent prompt → 重命名 `frontend-reviewer` | 半天 |
| 改 `harness-runtime/config/harness.yaml` 的 `interaction` stage 配置 | 10 分钟 |
| 加 `project-knowledge/engineering/policies/stage-rules.yaml` 前端栈 config | 10 分钟 |
| PRD 阶段补 API contract draft 模板 | 半天 |
| 写迁移文档 + 历史 mission 兼容策略 | 半天 |
| harness-lint 更新 | 小 |

**合计 ≈ 3-4 天**。

---

## 8. 风险与缓解（v2）

| 风险 | 影响 | 缓解 |
|---|---|---|
| reviewer 角色重叠（interaction 评 UX 与 code-review 评质量混评） | 中 | frontend-reviewer 只评四维（domain_coverage / surface_baseline / path_completeness / walkthrough_ready）；code-review / verify 接管质量门（a11y / lint / coverage / e2e）；职责按 stage 严格分层 |
| 后端按 draft types 实现完发现 contract 错 | 中（v2 概率更低） | tech-design 阶段 freeze types 前要求后端 review；execute 阶段如要改 types 必须发 Decision Gate；MSW 已不作契约证据，不存在 mock 漂移问题 |
| ~~Mock 漂移（mock 与真后端行为差异）~~ | ~~中~~ | **v2 删除该风险条款**：MSW 仅 interaction 阶段演示用，不作契约证据；execute 切真 API 后不做 contract test |
| interaction 阶段"效果到位但代码脆"——后续阶段才暴露 | 中 | code-review 是强制质量门：lint / typecheck / coverage / a11y 不达标无法进 verify；不接受"interaction PASS 等于代码合格" |
| 新前端 UI 需求在 execute 阶段出现 | 低 | breakdown 不允许产 `frontend_ui` 标签；如出现则 Decision Gate 路由回 interaction stage 处理 |
| Harness 框架历史 mission 不兼容 | 中 | `prototype.delivery_mode=interactive_prototype` 是默认值；历史 mission 继续走 interaction skill，新 mission 显式声明 `frontend_engineering` 才走 prototype-as-frontend skill |

---

## 9. 实施 Phase

**Phase 1 — 在 TheForce 当前 mission 验证**（不动 Harness 框架）
- 升级 demo 为生产级前端：MSW + React Query + 真 API client + Playwright + a11y
- 写 API contract 文档（shared types）
- 用户实际跑一遍，对比"看 HTML 变体审" vs "在浏览器点真原型审"的效率
- 3-4 天

**Phase 2 — 升级 Harness 框架**（基于 Phase 1 经验）
- 改 `interaction` stage 的 contract / skill / role 三处
- 写迁移文档
- 灰度 flag 控制单独原型 / 原型即前端交付 两种 interaction 模板共存
- 3-4 天

**Phase 3 — 用新 mission 验证新流程**
- 从头开发一个新 mission
- 验证 Phase 1 + Phase 2 的设计假设
- 1 个完整 mission cycle

---

## 10. 决策点

1. 是否走原型即前端路线？（是 / 否 / 先 Phase 1 验证）
2. TheForce 当前 demo 是否升级到生产级？（升级 / 当前够了 / 另开 mission）
3. 是否动 Harness 框架本身？（改 / 不改只改 demo / 等 Phase 1 完再定）
4. shared types 形态？（TS 包 / OpenAPI + ts-rest / 双轨）
