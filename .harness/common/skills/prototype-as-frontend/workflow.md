# 前端即原型交付阶段动作工作流

> **方法论参考**：`.harness/docs/methodologies/prototype-as-frontend-delivery.md`。
> **设计原则**：见同目录 `SKILL.md` 的"设计原则"段（交互阶段通用原则 + 本路线专属补充）；本工作流的不变式表是这些原则的可执行落点。

下文出现的所有 `harness ...` 命令一律通过 harness-cli 技能调用（默认带 `--json`、消费类型化载荷）。

<workflow stage="interaction" mode="frontend_engineering" version="2">

<goal>
在 `prototype.delivery_mode=frontend_engineering` 路线下，从产品定义阶段产出的产品定义包、领域模型、`api-contract-draft.md` 和任务契约出发，对长期前端工程做一次基于界面边界的增量变更：实现、修改或扩展真页面与真组件，让用户在浏览器跑通产品定义列出的所有用户路径（成功、错误、空态、权限），并落出 `lib/types/` 草案作为后续阶段冻结的契约草案。本阶段**不写 / 不跑 Playwright 端到端验证**，不做完整可访问性审计，不做覆盖率 / 代码风格阈值检查，这些由后续技术设计、执行、代码审查和验证阶段承接。
</goal>

<role>
你是交互阶段在 `frontend_engineering` 路线下的前端原型交付编排者。你不写交互说明 Markdown 文档，你通过 `frontend-prototype-engineer` 产出真前端代码、MSW 模拟、共享类型草案和 `frontend-changeset` 记录。本阶段的核心是“用户能看见效果”：所有路径在界面上可点可见，用户在浏览器走查通过。所有界面边界、页面、组件、状态、类型必须先从用户任务、信息架构和领域可见性决策推导，再可追溯到验收场景 / 条件和领域对象。
</role>

<invariants>

| 编号 | 检查 | 执行位置 |
|---|---|---|
| `use-case-realization-before-code` | 写前端代码前必须先说明已确认系统用例如何实现为用户路径、界面边界、状态、反馈和验收断言；不得从路由 / 组件清单倒推用户路径 | 步骤 1 + 审查员 `domain_coverage` 维度 |
| `domain-driven` | 界面边界 / 页面 / 组件 / 状态 / 用户动作必须从产品定义 `product-domain-model.md` 推导；每条改动有 `domain_refs` 字段；但禁止把领域实体一对一界面化，必须先说明用户任务、用例实现、信息架构和领域可见性决策 | 步骤 1 + 审查员 `domain_coverage` 维度 |
| `information-architecture-first` | 路由 / 页面 / 区块 / 面板 / 弹窗 / 列表 / 详情的层级必须服务用户任务和决策顺序；不得按领域实体机械拆页面 | 步骤 1 + 审查员 `domain_coverage` 维度 |
| `domain-visibility-decision` | 每个关键领域概念必须分类为主对象、支撑上下文、状态指示、动作入口或隐藏内部概念，并说明展示、折叠、合并或隐藏原因 | 步骤 1 + 审查员 `domain_coverage` 维度 |
| `surface-first-baseline` | 每条改动判断操作类型；非创建改动必须引 `baseline_ref`；不另起孤立界面边界 | 步骤 1 + 审查员 `surface_baseline` 维度 |
| `traceability-to-scenario` | 每条改动 `traces_to` 至少一个产品定义验收场景 / 条件；场景编号仅作为追溯锚点，并关联至少一个领域实体 / 动作 | 步骤 1 / 步骤 5 + 审查员 `domain_coverage` 维度 |
| `state-completeness` | 每个用户路径覆盖加载、空态、错误、权限、取消、重复、边界；例外项有说明。覆盖以 `state_action_matrix` 为载体，**行键＝每条 PRD/use-case 流步骤的结局态集合**（对齐 `use-case-model.md` 的流步骤扇出结局，等价 interactive 路线的 "beat"），逐路径按 7 类结局态核对、不适用项显式豁免 + 理由，禁止自由填清单而无覆盖分母 | 步骤 3 + 审查员 `path_completeness` 维度 |
| `visible-copy-zh-cn` | 用户可见文字默认中文；外语例外有理由 | 步骤 3 + 审查员 `walkthrough_ready` 维度 |
| `prd-feedback-gate` | 实施过程中若需要改产品定义、领域模型、验收场景 / 条件或范围，停下来发决策门；不静默修改 | 步骤 4a |
| `e2e-locator-ready` | 关键可交互元素测试标识 / 可访问性角色；关键状态可观察 DOM 标记；可断言点在变更清单列出 | 步骤 1 / 步骤 3 + 审查员 `path_completeness` 维度 |
| `knowledge-promotion` | 必须标出可沉淀项（模式、类型、定位器约定）供复盘评估 | 步骤 5 / 步骤 9 |
| `delivery-mode-frontend-engineering` | 仅在 `prototype.delivery_mode=frontend_engineering` 时启用；否则路由错误返回 BLOCKED 给 skill-router | 步骤 0 |
| `frontend-project-root-project-owned` | `{frontend_project_root}` 必须来自项目级规格 / 项目说明：优先 `project-knowledge/engineering/policies/stage-rules.yaml` 的 `interaction.frontend_project_root`，其次显式项目配置 `prototype.frontend_engineering.frontend_project_root`；不得由技能、专家角色或方法论默认目录硬编码 | 步骤 0 |
| `frontend-changeset-required` | 本次任务必须产出 `frontend-changeset.md`，列出界面边界改动清单、基线引用、`traces_to` 验收场景 / 条件 | 步骤 1 / 步骤 5 |
| `frontend-flowstep-coverage` | 门 A：PRD 流步骤全集（`use-case-model.md` 的 `SUC-xx-FLOW-xx`）必须 ⊆ `frontend-changeset.md` surfaces 机器表所有 `traces_to` 并集，或在结构化「界面承载豁免（N/A）」段声明；漏一个 `harness prototype-as-frontend changeset-check` 报 `FRONTEND_FLOWSTEP_NOT_IN_CHANGESET`(FAIL)。等价于 interactive_prototype 路线的 `UPSTREAM_FLOWSTEP_NOT_IN_GRAPH` | 步骤 1 / 步骤 5 / 步骤 8 + 审查员 `path_completeness` 维度 |
| `e2e-obligation-keyed-by-flowstep` | 门 B 下游键：`frontend-changeset.md` / 契约 `e2e_obligation[]` 以 PRD 流步骤为键；每条 PRD 流步骤声明 `status: required` 或 `accepted_alternative`+非空 `accepted_reason`；verify 阶段 `e2e_resolver` 以同一 flow-step 全集逐条核验（`frontend_flowstep_e2e_uncovered` FAIL）| 步骤 1 / 步骤 5 / 步骤 8 + verify 阶段 |
| `shared-types-draft-only` | `lib/types/**` 在本阶段是**草案**；冻结由技术设计阶段完成；不得在本阶段以“冻结契约”自居 | 步骤 2 |
| `no-e2e-in-interaction` | 本阶段不创建 Playwright 规格、不跑端到端验证；只做定位器 / 可访问性角色 / 断言点准备 | 步骤 3 / 步骤 4 |
| `no-quality-gates-in-interaction` | 不在本阶段执行代码风格 / 类型检查 / 覆盖率 / 可访问性阈值检查作为门禁条件（基础代码风格错误仍要修，但不作为通过门）| 步骤 4 |
| `reviewer-readonly` | `frontend-reviewer` 必须在只读子 Agent 中调用 | 子 Agent 注册表 `readonly=true` |
| `fix-then-recheck` | 任何工程修改后必须重新让用户走查并重新过审查员 | 步骤 6 / 步骤 7 |
| `msw-interaction-scope-only` | MSW 是本阶段的演示工具；后续阶段切真接口后不作为契约证据；本阶段不要求“覆盖镜像后端契约”，只要求“够用户走查所有路径” | 步骤 2 |
| `dev-server-port-safety` | 起 `pnpm dev` / 任何本地预览服务前先探测目标端口；端口被占用时改用空闲端口（`pnpm dev --port <free>` 或允许其自动递增），**不得 kill / stop / 抢占已在监听的进程**——本机可能并行运行其它项目的原型服务。启动后把实际 URL / 端口明确告诉用户 | 步骤 4 / 步骤 7 |

</invariants>

<entry>

- 任务切片 `control_plane.stage=interaction`。
- `harness config snapshot --json` 返回 `prototype.delivery_mode=frontend_engineering`。
- 上游产物齐全：`product/product-definition.md`、`product/product-domain-model.md`、`api-contract-draft.md`、`mission-contract.md`、`contracts/prd.contract.yaml`。
- 本任务确为前端 / UI 任务（前端工程路线默认按涉及 UI 处理；明确纯后端 / 接口 / 数据 / CLI 时不进本路线）。不再用 `harness interaction check-ui-trigger` 的 UIC 结论门控——要不要原型的判定已移到 interaction 阶段内。

</entry>

<exit>

- `{frontend_project_root}/` 已就绪：`pnpm install` 干净、`pnpm dev` 启动成功、产品定义列出的所有用户路径都能在浏览器看到。
- `frontend-changeset.md` 完整：主要用户任务、信息架构、领域可见性决策、本次界面边界改动清单、基线引用、`traces_to` 验收场景 / 条件、端到端定位器可断言点。
- `{frontend_project_root}/lib/types/**` 草案覆盖产品定义 `api-contract-draft.md` 全部接口。
- `{frontend_project_root}/mocks/**` 覆盖所有路径的 MSW 处理器和场景切换器。
- `contracts/prototype-as-frontend.contract.yaml` 已填充且 `harness contract check` PASS。
- `frontend-reviewer` 四维结论在等同严格度下全 PASS；或卡死后用户在 Decision Gate 上显式拥有残留风险的 approval 已记录（审查循环本身永不因轮次自动放行）。
- 用户浏览器走查检查点：实际跑通产品定义列出的全部用户路径（含成功、错误、空态、权限），记录写入 `harness-runtime/harness/traces/{mission_id}/user-walkthrough.md`。
- `harness prototype-as-frontend gate run` 返回 `status=pass`。

</exit>

<subagents>

| 角色 | 模式 | 范围 / 限制 | 包 |
|---|---|---|---|
| `frontend-prototype-engineer` | spawn | 可写 `{frontend_project_root}/**`（除 `tests/e2e/**`）+ `frontend-changeset.md` | `.harness/common/agents/frontend-prototype-engineer.md` |
| `frontend-reviewer` | spawn readonly | 禁止 Edit / Write / MultiEdit / NotebookEdit / Bash（除只读 pnpm 命令） | `.harness/common/agents/frontend-reviewer.md` |

</subagents>

<inputs>

| 引用 | 是否必需 | 平面 |
|---|---|---|
| `product/product-definition.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `product/product-domain-model.md` | true | Memory |
| `api-contract-draft.md` | true | Memory |
| `mission-contract.md` | true | Intent |
| `contracts/prd.contract.yaml` | true | Memory |
| `{frontend_project_root}/` 当前状态 | true（如存在，作为基线） | Memory |
| `project-context.md` | conditional: brownfield | Context |
| `project-knowledge/engineering/policies/stage-rules.yaml` (interaction 段，含 `frontend_project_root`) | conditional: frontend_engineering | Memory |
| `project-knowledge/_index.md` | conditional | Memory |
| `harness.yaml` | true via `harness config snapshot` | Memory |

</inputs>

<outputs>

| 产物 | 路径 | 类型 | 平面 / 校验器 |
|---|---|---|---|
| `frontend-project-patch` | `{frontend_project_root}/`（本次新增 / 修改 / 扩展的文件） | 可运行代码库 | Memory + Evidence |
| `frontend-changeset` | `harness-runtime/harness/artifacts/{mission_id}/interaction/frontend-changeset.md` | markdown | Memory |
| `shared-types-draft` | `{frontend_project_root}/lib/types/**` | TS 源码（草案） | Memory |
| `msw-handlers` | `{frontend_project_root}/mocks/**` | TS 源码 | Memory |
| `user-walkthrough` | `harness-runtime/harness/traces/{mission_id}/user-walkthrough.md` | markdown | Evidence |
| `prototype-as-frontend-contract` | `harness-runtime/harness/stages/{mission_id}/contracts/prototype-as-frontend.contract.yaml` | 契约 | `harness contract check --upstream prd.contract.yaml --upstream mission-contract.contract.yaml` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化 + delivery_mode / 界面触发判断 + frontend_project_root 解析">

- 调用 `harness mission stage start --mission <mission-id> --stage interaction --json`。
- 调用 `harness trace log-init --mission <mission-id> --stage interaction --json`。
- 调用 `harness config snapshot --json`，提取：
  - `prototype.delivery_mode`：必须是 `frontend_engineering`；否则返回路由错误给 skill-router（应该调度 `interaction` 技能）。
  - `prototype.frontend_engineering.frontend_project_root` 与 `frontend_project_root_source`（如命令行提供）：只接受项目级来源；不得使用技能、专家角色或方法论默认目录。
  - `prototype.frontend_engineering.api_contract_draft_required`：若为 true 但上游缺 `api-contract-draft.md`，返回 BLOCKED 路由回产品定义阶段。
- 调用 `harness context check --json`；PASS 则读 `project-context.md`。
- 调用 `harness interaction check-ui-trigger --mission <mission-id> --json`。
- 调用 `harness frame current --mission <mission-id> --json`，校验 `mission_slice.control_plane.stage=interaction` 且 `lane_action.skill=prototype-as-frontend`。
- 解析 `{frontend_project_root}`：
  1. 先读取 `project-knowledge/engineering/policies/stage-rules.yaml` 的顶层 `interaction.frontend_project_root`。
  2. 若缺失，再读取明确项目说明：`project-context.md`、`project-knowledge/context/repository-map.md` 或 `project-knowledge/context/tech-stack.md` 中对前端工程根目录的声明。
  3. 若仍缺失，才使用 `harness config snapshot` 中显式填写的 `prototype.frontend_engineering.frontend_project_root`。
  4. 若仍无法解析，返回 `frontend-project-root-unresolved`，发起决策门询问用户应使用哪个目录；用户确认后先回写项目级规格 / 项目说明，再继续本阶段。
- 若 `project-knowledge/engineering/policies/stage-rules.yaml` 存在 `interaction:` 段，读取其前端栈固化项作为本次实施基线；缺失时只允许使用方法论 §3 的技术栈建议作为待确认默认，不得顺带决定前端工程目录。

</step>

<step id="step-1" n="1" goal="frontend-prototype-engineer 调度 + 用户任务 / 信息架构 + 界面边界基线判断 + frontend-changeset.md 起草">

<dispatch role="frontend-prototype-engineer" mode="spawn" />

任务信封必须包含：

- 任务目标：对长期前端工程 `{frontend_project_root}/` 做本次任务的界面边界增量变更，让产品定义列出的所有用户路径在浏览器可见可点；产出 `frontend-changeset.md` 记录本次改动。
- 输入路径和已读摘要：`product-definition.md`、`product-domain-model.md`、`api-contract-draft.md`、`mission-contract.md`、`prd.contract.yaml`、`project-context.md`（如有）、`project-knowledge/engineering/policies/stage-rules.yaml`（interaction 段）、`{frontend_project_root}/` 当前状态。
- 输出路径：`{frontend_project_root}/**`（除 `tests/e2e/**`）+ `harness-runtime/harness/artifacts/{mission_id}/interaction/frontend-changeset.md`。
- 设计原则引用：本技能 `SKILL.md` 的"设计原则"段（领域驱动 / 界面边界优先 / 可追溯 / 状态完整 / 中文文案 / 产品定义回流 / 端到端定位器 / 长期沉淀）。
- 完成条件（本步只起草）：
  - 从产品定义路径、验收场景 / 条件、角色、权限、领域命令中识别 `primary_user_tasks`、决策时刻、失败时刻
  - 完成 `use_case_realization`：把已确认系统用例、主成功流、备选流、异常流、界面承载要求映射到路由 / 页面 / 区块 / 状态 / 反馈 / 定位断言义务
  - 推导 `information_architecture`：路由 / 页面 / 区块 / 面板 / 弹窗 / 抽屉 / 列表 / 详情的层级和导航关系
  - 完成 `domain_visibility_decisions`：关键领域概念分类为 `primary_object` / `supporting_context` / `state_indicator` / `action_affordance` / `hidden_internal`，并说明展示、折叠、合并或隐藏原因
  - 界面边界基线判断完成：对 `{frontend_project_root}/app/` / `components/domain/` / `lib/types/` 现有内容做盘点
  - `frontend-changeset.md` 起草（用 `harness-runtime/templates/frontend-changeset.md` 模板）：先记录 `primary_user_tasks`、`use_case_realization`、`information_architecture`、`navigation_model`、`domain_visibility_decisions`、`surface_model`、`state_action_matrix`，再填「界面边界改动清单（surfaces，机器段）」固定列表（每行 `surface_id | kind: route/page/component/type | operation: create/modify/extend/retire | file_path | baseline_ref（create 时 null/-，其它必填）| traces_to（验收场景 SCN-xx + 承载的 PRD 流步骤 SUC-xx-FLOW-xx[.state]，空白/逗号/顿号分隔）| domain_refs（Entity:/State:/Action:）`），并填「界面承载豁免（N/A）」段（非界面承载的流步骤 / SUC / 节拍：`prd_node_id | 豁免粒度 suc/flowstep/beat | 理由 | 责任归属`）与「端到端义务（e2e_obligation）」段（以 PRD 流步骤为键）。
    - **门 A 自检（不变式 `frontend-flowstep-coverage`）**：PRD 流步骤全集必须被 surfaces 机器表 `traces_to` 并集覆盖或在 N/A 段豁免，缺一即 `FRONTEND_FLOWSTEP_NOT_IN_CHANGESET`。
    - **门 B 自检（不变式 `e2e-obligation-keyed-by-flowstep`）**：每条 PRD 流步骤在 `e2e_obligation[]` 有键，`status=required` 或 `accepted_alternative`+非空 `accepted_reason`。
  - 每条改动指出承载哪个用户任务、领域实体 / 状态 / 动作，以及该领域概念为什么应该可见
  - 每条改动指出对应产品定义验收场景 / 条件

frontend-prototype-engineer 必须完成：

- 在写组件和模拟数据前先完成用户任务、用例实现矩阵、信息架构、导航模型和领域可见性决策；不得先把领域对象铺成页面再补解释。
- 不得把领域实体一对一做成页面、表格、卡片或表单；任何可见对象都必须说明它服务的用户任务、决策点或反馈路径。
- 对领域模型中的关键概念必须明确分类：主对象、支撑上下文、状态指示、动作入口、隐藏内部概念。
- 判断本次界面边界操作类型组合：`create_surface` / `modify_surface` / `extend_surface` / `retire_surface` / `supersede_surface`（迭代取代：用新路由 / 组件换代既有界面、承接覆盖、不与旧界面并存）（不变式 `surface-first-baseline`）。
- 修改既有界面边界必须引用既有路由 / 组件 / 类型作为基线；不得生成孤立新界面边界。
- 每个改动必须能映射到领域模型中的实体 / 状态 / 动作（不变式 `domain-driven`）。
- 每个改动必须 `traces_to` 至少一个验收场景 / 条件，并把该改动承载的 PRD 流步骤 `SUC-xx-FLOW-xx` 一并写进 `traces_to`（门 A 覆盖判据来源）；场景编号只作为证据追溯锚点（不变式 `traceability-to-scenario` / `frontend-flowstep-coverage`）。
- 变更清单 `e2e_obligation[]` 段以 PRD 流步骤为键列出每条流步骤的“可被端到端断言点”（定位器 / 角色 + 可访问名称 / 可观察 DOM 标记 + `status`），但不写规格（不变式 `e2e-locator-ready` / `e2e-obligation-keyed-by-flowstep`）。

</step>

<step id="step-2" n="2" goal="共享类型草案 + 接口客户端 + MSW 处理器 + 场景">

由 frontend-prototype-engineer 继续：

- `{frontend_project_root}/lib/types/`：从 `api-contract-draft.md` 抽出所有接口的请求 / 响应类型、领域实体、状态枚举、值对象和错误类型。
  - **本阶段是草案**，允许后续技术设计阶段反馈调整；不在本阶段以“冻结契约”自居。
- `{frontend_project_root}/lib/api/`：fetch 包装层。业务代码只调这里；模拟数据与真后端切换由本层封装，业务代码不感知。
- `{frontend_project_root}/mocks/handlers/`：每个接口一个处理器，响应类型从 `lib/types/` 引入；不得用 any。
- `{frontend_project_root}/mocks/fixtures/`：可重用测试数据。
- `{frontend_project_root}/mocks/scenarios/`：演示分支切换器，**必须覆盖所有路径**（成功 / 错误 / 空态 / 权限 / 边界），界面在开发 / 预览环境暴露切换控件。
- 业务代码（`mocks/` 之外）禁止出现 `if (process.env.NEXT_PUBLIC_MOCK)` 之类条件分支。
- **本阶段不要求 MSW 镜像真后端契约**：MSW 只是本阶段的演示工具；目标是“够用户走查所有路径”，不是“作为契约证据”。

</step>

<step id="step-3" n="3" goal="页面 + 组件 + 全路径实现">

由 frontend-prototype-engineer 继续：

- 按产品定义用户旅程实现页面（`app/<route>/page.tsx`）和组件（`components/domain/**`）。
- 状态管理用 React Query（服务端状态）；表单用 react-hook-form + zod；界面用 shadcn/ui。
- **必须覆盖所有路径**（不变式 `state-completeness`）：加载、空态、错误（网络 / 业务 / 校验 / 服务不可用）、权限不足、重复提交、取消、返回、刷新。
  - **`state_action_matrix` 导出规程（覆盖分母固定）**：不要自由列状态清单。以 `use-case-model.md` 每条 PRD 流步骤（`SUC-xx-FLOW-xx`）的结局态集合为**行键**——即把该流步骤的扇出结局（成功 / 各类失败 / 空 / 权限拒绝 / 取消…）当作 interactive 路线的 "beat" 同构展开，每个结局态一行。逐行按 7 类结局态（加载、空态、错误、权限、取消、重复、边界）核对界面承载：每类要么落到具体界面状态 + 可观察 DOM 标记，要么显式标 `N/A` 并写理由（如"该流步骤无外部依赖故无加载态"）。任何流步骤的某类结局态既未承载又未豁免即为覆盖缺口。
  - （建议后续加 `FRONTEND_PATH_STATE_INCOMPLETE` 子门，以 `use-case-model.md` 流步骤结局态全集为分母核对 `state_action_matrix` 行键，与 interactive 路线的 beat 门同构。）
- 主流程页面必须有 ErrorBoundary + Suspense；不接受白屏 / unhandled rejection。
- 所有用户可见文字默认中文；外语例外必须在变更清单标注理由（不变式 `visible-copy-zh-cn`）。
- 关键可交互元素必须有 `data-testid` 或语义化 ARIA 角色 + 可访问名称；关键状态有可观察 DOM 标记（不变式 `e2e-locator-ready`）。
- **不写 Playwright 规格 / 不在 `tests/e2e/` 创建文件**：本阶段权限已禁止。
- **不要求可访问性评分达标 / 不要求覆盖率达项目阈值**：这些由代码审查和验证阶段承接。

</step>

<step id="step-4" n="4" goal="基本健康检查（非门禁）">

由 frontend-prototype-engineer 继续：

- 跑基础健康检查（保证用户能走查）：
  - `pnpm install` → `harness-runtime/harness/traces/{mission_id}/install.log`
  - `pnpm dev` 启动成功，主路径返回 200 → `traces/{mission_id}/dev-startup.log`（遵守 `dev-server-port-safety`：先探测端口，被占用就换空闲端口，绝不停掉已在跑的服务）
  - 关键编译错误必须修复（不允许"以后再说"）
- **不在本阶段强制**：完整代码风格阈值、完整类型检查阈值、覆盖率、Playwright 端到端验证、axe-core 可访问性评分。基础 TypeScript / 构建错误必须修，质量门由代码审查和验证承接。

</step>

<step id="step-4a" n="4a" goal="产品定义回流检查">

- 对照 `product-definition.md`、`product-domain-model.md`、`prd.contract.yaml`，检查实施是否引入新的用户目标、验收场景 / 条件、领域实体、实体状态、用户动作、权限规则或范围变化（不变式 `prd-feedback-gate`）。
- 若只是把既有产品定义内容表达为界面和状态，进入契约写入。
- 若需要改变产品定义内容，停止推进，将差异写入 `frontend-changeset.md` 的「产品定义回流检查」段和契约的 `prd_feedback` 段，发起决策门或路由回产品定义阶段。
- 不得直接修改产品定义包或差量规格。

</step>

<step id="step-5" n="5" goal="contract.yaml 初始化 + execution_result 写入">

- 若 `contracts/prototype-as-frontend.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage interaction --template prototype-as-frontend --json`。
- 调用 `harness contract add-execution-result --artifact harness-runtime/harness/stages/<mission-id>/contracts/prototype-as-frontend.contract.yaml --result <frontend-prototype-engineer-execution-result.yaml> --json`。
- 调用 `harness contract patch`，把以下字段从 `frontend-changeset.md` 和工程实际形态抽取写入 `contract.yaml`：
  - `frontend_project.root` = 实际 `{frontend_project_root}`
  - `frontend_changeset.primary_user_tasks[]` = 变更清单中的主要用户任务
  - `frontend_changeset.information_architecture` = 变更清单中的路由 / 页面 / 区块 / 导航 / 决策顺序
  - `frontend_changeset.domain_visibility_decisions[]` = 变更清单中的主对象 / 支撑上下文 / 状态指示 / 动作入口 / 隐藏内部概念分类与理由
  - `frontend_changeset.surface_model[]` = 变更清单中的界面边界模型
  - `frontend_changeset.state_action_matrix[]` = 变更清单中的状态 / 动作 / 可观察反馈映射
  - `frontend_changeset.surfaces[]` = 变更清单 surfaces 机器表全量（每行含 `traces_to` 承载的 PRD 流步骤）
  - `frontend_changeset.na_exemptions[]` = 变更清单「界面承载豁免（N/A）」段全量
  - `frontend_changeset.flowstep_coverage` = 门 A 覆盖结论（`prd_flowsteps` / `traced_flowsteps` / `na_flowsteps` / `uncovered_flowsteps`），`uncovered_flowsteps` 非空即 FAIL
  - `api_contract_draft.endpoints[]` = 从 `lib/types/` 与 `api-contract-draft.md` 比对生成
  - `msw_coverage.scenarios[]` = 从 `mocks/scenarios/` 抽取
  - `e2e_obligation[]` = 以 PRD 流步骤为键的端到端义务（`flow_step`/`surface_id`/`traces_to`/`status: required|accepted_alternative`/`accepted_reason`/`locator`/`assertable_states`；替代旧 `e2e_locator_obligations[]`，给后续技术设计 / 执行 / 验证阶段用，verify 以 flow-step 全集逐条核验）
  - `obligations[].traces_to.ac` 命中产品定义验收场景 / 条件对应的追溯锚点
  - `knowledge_promotion_candidates[]` 列出可沉淀项
- 调用 `harness contract check --artifact contracts/prototype-as-frontend.contract.yaml --upstream prd.contract.yaml --upstream mission-contract.contract.yaml --json`；FAIL 必须修复。

</step>

<step id="step-6" n="6" goal="frontend-reviewer 循环（四维结论）">

无轮次放行（轮次只记录修复历史，永不放行）；本轮 `frontend-reviewer` 在等同严格度下返回整体 PASS 时退出。

<dispatch role="frontend-reviewer" mode="spawn" />

审查简报必须包含：

- `{frontend_project_root}` 路径 + `frontend-changeset.md` + 产品定义包 + `api-contract-draft.md` + `contracts/prototype-as-frontend.contract.yaml`。
- 设计原则引用：本技能 `SKILL.md` 的"设计原则"段（审查员评审依据）。
- 四维结论要求：**domain_coverage**（用户任务 + 信息架构 + 领域可见性 + 可追溯，且没有领域模型一对一机械界面化）、**surface_baseline**（界面边界优先 + 基线 + 变更清单）、**path_completeness**（状态完整 + 端到端定位器就位 + MSW 覆盖所有路径）、**walkthrough_ready**（用户能在浏览器点遍 + 中文文案 + `lib/types/` 草案覆盖 + 场景切换器可用）；任一未 PASS 整体不 PASS。
- 明确告知审查员：本阶段**不评端到端充分性 / 可访问性评分 / 覆盖率 / 代码风格阈值**，这些是代码审查 / 验证阶段的事；本阶段评的是“效果到位 + 共性约束遵守”。

每轮审查返回后由控制面记录审查结论；不再用 `patch --add-round` 手工维护轮次：

```bash
harness contract record-review --artifact harness-runtime/harness/stages/<mission-id>/contracts/prototype-as-frontend.contract.yaml --role frontend-reviewer --verdict <PASS|PASS_WITH_RISK|HOLD|BLOCKED> --subagent-id <dispatch-id> --model <resolved-model> --review-basis harness-runtime/harness/artifacts/<mission-id>/interaction/frontend-changeset.md --summary <review-summary> --json
```

处理审查结论：

- HOLD / BLOCKED：先用 `harness contract record-review` 记录 verdict 与 `--blocking-gap`，再按缺口修复变更清单、工程代码、MSW、`lib/types` 草案，重启开发服务验证主路径，再重入审查员。
- PASS：用 `harness contract record-review` 记录 PASS，退出循环。
- 无轮次放行：轮次只记录修复历史，永不构成放行理由，每轮以等同严格度重审，循环到 reviewer 在等同严格度下 PASS 为止。卡死时（同一阻断在修复后仍以相同根因连续 HOLD 且无实质进展，按缺口本质判断、不是"轮次到点"）不得降级通过，询问用户选择解决方向（候选**不含"接受降级批准"**：继续修 / 改范围 / 升级 BLOCKED），残留风险只能由用户在充分披露后于 Decision Gate 显式拥有并记 approval。

</step>

<step id="step-7" n="7" goal="用户浏览器走查检查点">

- 启动 `pnpm dev`，把 URL 给用户（遵守 `dev-server-port-safety`：先探测端口占用，被占用就用 `--port <free>` 换空闲端口，绝不 kill / stop 其它项目已在跑的服务；把实际端口 / URL 明确告诉用户）。
- 由用户在浏览器实际操作前端，跑通产品定义列出的全部用户路径（成功 / 错误 / 空态 / 权限），通过场景切换器观察各分支。
- 主流程把走查结果写入 `harness-runtime/harness/traces/{mission_id}/user-walkthrough.md`，含：
  - 每个路径 × 每个验收场景 / 条件的 PASS / FAIL + 用户文字反馈
  - 演示分支切换是否符合预期
  - 用户可见文案是否准确（中文 / 例外）
  - 用户对继续推进的明确意见
- 若用户走查 FAIL：按反馈回步骤 3 修复，重新进入审查员循环。
- 若用户走查 PASS：调用 `harness approval append --mission <mission-id> --type checkpoint --stage interaction --status approved --json`。

</step>

<step id="step-8" n="8" goal="产物门禁自检">

- 调用 `harness contract check --artifact contracts/prototype-as-frontend.contract.yaml --upstream prd.contract.yaml --upstream mission-contract.contract.yaml --json`。
- 调用 `harness prototype-as-frontend changeset-check --mission <mission-id> --json`：校验 `frontend-changeset.md` 先有主要用户任务、信息架构、领域可见性决策，再校验每条改动都有基线引用（如非创建）、追溯关系和领域引用；并执行**门 A**：解析 surfaces 机器表与 N/A 豁免段，PRD 流步骤全集 ⊆ `traces_to` 并集 ∪ N/A，漏一个 `FRONTEND_FLOWSTEP_NOT_IN_CHANGESET`(FAIL)；surfaces 表解析为空 `FRONTEND_CHANGESET_SURFACES_UNPARSEABLE`(FAIL)；声明豁免但已被 trace 的流步骤 `FRONTEND_NA_EXEMPTION_STALE`(WARN)。任何 FAIL 必须修复。
- 调用 `harness prototype-as-frontend path-check --mission <mission-id> --json`：校验每个用户路径都有界面实现 + MSW 处理器 / 场景 + 定位器标记。
- 调用 `harness alignment check --mission <mission-id> --stage interaction --json`：验证界面边界 / 页面 / 状态对齐产品定义和领域模型。
- 调用 `harness prototype-as-frontend gate run --mission <mission-id> --json`：聚合上述检查 + 审查员结论 + 用户走查批准。

</step>

<step id="step-9" n="9" goal="阶段完成 + 工作图输出">

- 调用 `harness mission stage complete interaction --mission <mission-id> --json`。
- `lane_action.output_artifact` = `{frontend_project_root}/`（本次增量变更的产物视为对长期前端工程的增量）；补充产物包含 `frontend-changeset.md`、共享类型草案、模拟数据和用户走查记录。
- 在 contract YAML 的 `work_graph_artifact.artifact_refs[]` 段引用本次前端变更说明和 interaction-spec 等 artifact store 路径；长期前端工程目录只作为 living codebase 被引用，不复制进 Work Graph。
- `knowledge_promotion_candidates` 段记录可沉淀的前端模式、组件、共享类型模式、MSW 模式、定位器约定；复盘时由 planning-analyst 评估是否进入项目知识。
- 提示后续阶段：本阶段不交付端到端验证、覆盖率、可访问性评分；技术设计阶段需要冻结共享类型并产出端到端测试计划，执行阶段实现端到端验证、联调和测试加固，代码审查阶段做完整可访问性、代码风格和覆盖率审计，验证阶段跑真后端端到端验证。

</step>

</steps>

<failure_paths>

| 失败项 | 触发条件 | 处理 |
|---|---|---|
| `delivery-mode-mismatch` | 步骤 0 发现 `prototype.delivery_mode` 不是 `frontend_engineering` | 返回 BLOCKED 给 skill-router，请求路由到 `interaction` 技能 |
| `frontend-project-root-unresolved` | 步骤 0 无法从项目级规格 / 项目说明 / 显式项目配置解析 `frontend_project_root` | 发起决策门让用户指定路径；确认后先回写 `project-knowledge/engineering/policies/stage-rules.yaml` 或项目说明，再继续 |
| `api-contract-draft-missing` | 步骤 0 上游缺 `api-contract-draft.md` 且 `api_contract_draft_required=true` | 返回 BLOCKED，路由回产品定义阶段补齐 |
| `pnpm-install-fail` | 步骤 1 安装失败 | 检查 node 版本 / pnpm 配置 / 依赖冲突；不能跳 |
| `pnpm-dev-fail` | 步骤 4 开发服务启动失败或主路径 5xx / 白屏 | 修复后才能继续 |
| `surface-baseline-missing` | 步骤 1 / 步骤 8 变更清单缺基线引用（非创建操作） | 回步骤 1 引用既有界面边界或重新判断操作类型 |
| `traceability-incomplete` | 步骤 5 / 步骤 8 缺主要用户任务 / 信息架构 / 领域可见性决策，或改动缺验收场景 / 条件追溯 / 领域引用 | 回步骤 1 补齐；可能触发产品定义回流 |
| `path-incomplete` | 步骤 8 用户路径缺界面 / MSW / 场景 / 定位器 | 回步骤 2 / 步骤 3 补齐 |
| `prd-feedback-required` | 步骤 4a 发现实施需要改变产品定义 / 领域模型 / 验收场景 / 条件 / 范围 | 停止推进，记录差异，发起决策门或路由回产品定义阶段 |
| `frontend-reviewer-blocked` | 步骤 6 返回 BLOCKED | 按缺口修复重启开发服务，回审查员 |
| `review-stuck` | 步骤 6 卡死（修复后仍以相同根因连续 HOLD 无实质进展，非轮次到点） | 重新归因后进入用户检查点（候选仅：继续修 / 改范围 / 升级 BLOCKED，不含降级批准） |
| `user-walkthrough-fail` | 步骤 7 用户走查 FAIL | 按反馈回步骤 3，不得跳过 |
| `gate-fail` | 步骤 8 `harness prototype-as-frontend gate run` FAIL | 按失败检查回步骤 3 / 步骤 5 修复 |

</failure_paths>

</workflow>
# prototype-as-frontend references

本目录存放本 skill 在执行时按需参考的细化材料。骨架仅在 SKILL.md 和 workflow.md，避免会话启动时全量加载。

## 现有 references

- [stage-rules-interaction-template.yaml](stage-rules-interaction-template.yaml) — 项目级前端栈固化模板（写入 `project-knowledge/engineering/policies/stage-rules.yaml` 的 `interaction:` 段）。

## 方法论参考

- `.harness/docs/methodologies/prototype-as-frontend-delivery.md`（install 后位于 `.harness/docs/methodologies/prototype-as-frontend-delivery.md`） — 完整命题、流程、技术栈、目录结构、Mock 策略、Harness 框架改动、风险与缓解、实施 Phase。
