# Interaction lane action 工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §4（state matrix、错误路径、accessibility）+ `.harness/docs/workflow-authoring.md` + `visual-interaction-design` 子流程
> **设计原则**：见同目录 `SKILL.md` 的"设计原则"段；本 workflow 的 invariants 表是这些原则的可执行落点。

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用。

<workflow stage="interaction" version="2">

<goal>
从 PRD 阶段产出的产品定义包、DDD 领域模型、差量 spec + Mission Contract 出发，按 `control_plane.stage=interaction` 在 solution 之前产出对长期 prototype project 的结构化 patch、用户旅程、状态矩阵和派生交互证据。Interaction 产物按 `light` / `standard` / `deep` 分档：核心合同必须可实现、可验证、可追溯；可视化资产和拆分文件按任务复杂度生成，不以文件数量证明设计质量。结果落入 interaction.md + interaction-spec/ + contracts/interaction.contract.yaml + 按需 visual-interaction/，由 interaction-reviewer 审查通过。
</goal>

<role>
你是原型交互设计者，先从产品定义和 DDD 领域模型推导系统 surface、领域对象、Domain Command、状态、权限和业务反馈，再做用户路径分解（happy / 错误 / 空态 / 权限 / 键盘焦点），最后生成可视化资产。所有 surface / flow / state 必须可追溯到 AC，并可被 E2E locator 定位。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `visual-manifest-via-cli` | `visual-interaction-manifest.json` 不得被 agent 直接 Write/Edit，必须经 CLI 生成 | `design.interaction` overlay deny `Write(**/visual-interaction-manifest.json)` |
| `reviewer-readonly` | `interaction-reviewer` 必须在 readonly subagent 中调用 | subagent registry `readonly=true` |
| `webfetch-via-ask` | WebFetch / WebSearch 走 ask channel | `design.interaction` overlay ask |
| `fix-then-recheck` | `interaction.md` 修改后必须重新过 reviewer | `design-interaction-check-pending-recheck` hook |
| `prd-feedback-gate` | 原型设计若需要新增/修改 AC、用户旅程、领域模型或范围，必须回流 PRD / Decision Gate | Step 3a |
| `interaction-spec-canonical` | `interaction-spec/` 是下游 AI 的 canonical 原型实现合同；需要人类确认时 `prototype/index.html` 是唯一默认人类入口 | Step 1 / Step 2 |
| `surface-first-prototype` | `interaction-spec/` 必须按真实系统 surface / bounded context / navigation node 组织 | Step 1 |
| `prototype-project-patch` | 长期原型视为 prototype project；本次 `interaction-spec/` 是 patch | Step 6 |
| `prototype-visible-copy-zh-cn` | 原型、HTML / SVG 变体和 preview 中的用户可见文字默认必须使用中文 | Step 1 / Step 2 / Step 4 |
| `operable-prototype-first` | 选择 standard / deep 档或 workflow 要求可视化证据时，`visual-interaction/prototype/index.html` 必须是主入口、高还原、可操作页面；评审说明、AC / trace、Flow / State 展板和组件目录不得混入主原型页面 | Step 2 / Step 5 |

</invariants>

<entry>

- Mission Slice `control_plane.stage=interaction`。
- `harness interaction check-ui-trigger` 返回 `requires_interaction=true`；该检查默认 true，只有明确 API-only / 无界面 / 纯后端 / CLI-only 时允许 false。

</entry>

<exit>

- `interaction.md` 写入 design stage worktree。
- `interaction-spec/` 写入 AI handoff 合同。light 档至少含 README、surface-map、interaction-contract；standard / deep 按复杂度补充 information-architecture、surfaces/**、view-models.ts、checks、visual evidence 等。
- `contracts/interaction.contract.yaml` 已填充且 `harness contract check` PASS。
- standard / deep 档或 workflow 要求视觉证据时，`visual-interaction/visual-interaction-manifest.json` 由 `harness evidence visual manifest` 生成。
- standard / deep 档或 workflow 要求视觉证据时，`visual-interaction/prototype/index.html` 存在并通过 `harness interaction visual-coverage-check` 的主原型检查。
- `interaction-reviewer` PASS 或用户降级 approval 已记录。
- `harness interaction gate run` 返回 `status=pass`，且 alignment check PASS。

</exit>

<permissions>

<!-- design stage overlay：install pipeline 经 stage overlay key 从 design.interaction.json 物化；此处镜像关键权限，供 workflow 自文档化。 -->

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(**/visual-interaction-manifest.json)` | manifest 必须经 harness evidence visual manifest CLI 生成 |
| deny | `Bash(git push --force *)` | interaction 阶段禁止 |
| deny | `Bash(git reset --hard *)` | interaction 阶段禁止 |
| deny | `Write/Edit(harness-runtime/harness/stages/*/contracts/interaction.contract.yaml)` | contract 必须经 harness contract init/patch |
| deny | `Write/Edit(harness-runtime/harness/stages/*/solution.md)` | lane action 单一性 |
| deny | `Write/Edit(harness-runtime/harness/stages/*/tech-design.md)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/contracts/solution.contract.yaml)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/contracts/tech-design.contract.yaml)` | lane action 单一性 |
| ask | `WebFetch(*)` | 视觉证据收集需用户授权 |
| ask | `WebSearch(*)` | 视觉证据收集需用户授权 |
| allow | `Write(harness-runtime/harness/stages/*/interaction.md)` | interaction lane 主产物 |
| allow | `Write(harness-runtime/harness/stages/*/interaction-spec/**)` | AI handoff 原型合同 |
| allow | `Write(harness-runtime/harness/stages/*/visual-interaction/variants/**)` | 视觉资产 |
| allow | `Write(harness-runtime/harness/stages/*/visual-interaction/prototype/**)` | 主可操作原型 |
| allow | `Write(harness-runtime/harness/stages/*/visual-interaction/evidence/**)` | 内部审查证据 |
| allow | `Write(harness-runtime/harness/stages/*/visual-interaction/design-brief.md)` | design brief |
| allow | `Bash(harness *)` | interaction lane CLI 必需 |

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `interaction-designer` | spawn | 可写 `interaction.md`、`interaction-spec/**`、`visual-interaction/variants/**`、`visual-interaction/prototype/**`、`visual-interaction/evidence/**`、`visual-interaction/design-brief.md` | `.harness/common/agents/interaction-designer.md` |
| `interaction-reviewer` | spawn readonly | 禁止 Edit / Write / MultiEdit / NotebookEdit / Bash | `.harness/common/agents/interaction-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `product/product-definition.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `product/product-domain-model.md` | true | Memory |
| `mission-contract.md` | true | Intent |
| `project-context.md` | conditional: brownfield | Context |
| `project-knowledge/specs/_index.md` | conditional: `spec.enabled=true` | Memory |
| `project-knowledge/engineering/patterns/README.md` | conditional | Memory |
| `project-knowledge/design/decisions/README.md` | conditional | Memory |
| `project-knowledge/product/workflows/README.md` | conditional | Memory |
| `project-knowledge/product/prototype/README.md` | conditional | Memory |
| `project-knowledge/product/ui-surfaces/README.md` | conditional | Memory |
| `harness.yaml` | true via `harness config snapshot` | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `interaction-md` | `harness-runtime/harness/stages/${mission-id}/interaction.md` | markdown | Memory |
| `interaction-spec-dir` | `harness-runtime/harness/stages/${mission-id}/interaction-spec/` | prototype contract pack | Memory |
| `interaction-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/interaction.contract.yaml` | contract | `harness contract check --upstream prd.contract.yaml --upstream mission-contract.contract.yaml` |
| `visual-manifest` | `harness-runtime/harness/stages/${mission-id}/visual-interaction/visual-interaction-manifest.json` | manifest | Evidence; standard / deep 档或 workflow 要求视觉证据时生成 |

</outputs>

<steps>

<step id="step-0" n="0" goal="Stage 初始化 + delivery_mode / UI 触发判断">

- 调用 `harness mission stage start --mission <mission-id> --stage interaction --json`。
- 调用 `harness trace log-init --mission <mission-id> --stage interaction --json`。
- 调用 `harness config snapshot --json`，读取 stage policy、model routing、spec 开关、interaction gate 配置和 `prototype.delivery_mode`。
- 若 `prototype.delivery_mode=frontend_engineering`：返回路由错误给 skill-router，请求改派 `prototype-as-frontend` skill；本 skill 不处理该路线。仅在 `prototype.delivery_mode=interactive_prototype`（默认）时继续。
- 调用 `harness context check --json`；PASS 则读 `project-context.md`。
- 调用 `harness interaction check-ui-trigger --mission <mission-id> --json`。只有上游明确声明 API-only / 无界面 / 纯后端 / CLI-only 时允许 `requires_interaction=false`，此时返回路由错误并改走其它 lane。
- 调用 `harness frame current --mission <mission-id> --json`，校验 `mission_slice.control_plane.stage=interaction`。

</step>

<step id="step-1" n="1" goal="interaction-designer 调度 + interaction.md 起草">

通过 `@interaction-designer` native delegation调用 `interaction-designer` subagent（Cursor auto-routes 到对应 agent registry 项）

Task Envelope 必须包含：

- 任务目标。
- 输入路径和已读摘要：产品定义包、Mission Contract、`project-context.md`、相关 delta specs、长期 spec / pattern / decision / prototype project / UI surface 索引摘要。
- 输出路径：`interaction.md`、`interaction-spec/**`、`visual-interaction/variants/**`、`visual-interaction/prototype/**`、`visual-interaction/evidence/**`、`visual-interaction/design-brief.md`。
- write_scope：仅限 interaction lane 主产物、AI handoff 原型合同和可视化交互资产。
- 完成条件：artifact tier 选择理由、affected surface 清单、既有界面 baseline、prototype patch、surface changeset、DDD 领域模型覆盖、domain command 到 UI action 映射、state matrix、permission flow、AI handoff spec、验证义务、原型可见文案默认中文；standard / deep 档还必须包含 `prototype/index.html` 主可操作原型和 visual artifact refs。

interaction-designer 必须完成：

- 判断本次原型操作类型：`create_surface`、`modify_surface`、`extend_surface`、`retire_surface` 或组合。
- 修改既有界面时引用既有 surface baseline；不得生成孤立新页面。
- 产出 `interaction-spec/README.md` 作为 AI handoff 入口，明确阅读顺序、权威边界、artifact tier 和更新规则。
- light 档至少产出 `interaction-spec/surface-map.md` 与 `interaction-spec/interaction-contract.md`，集中记录 source trace、surface baseline / changeset、domain mapping、flows、states、interactions、scenarios、validation rules、consistency checks。
- standard / deep 档按复杂度拆分 `information-architecture.md`、`surfaces/**`、`view-models.ts`、`checks.md` 等；不得为了凑文件而填模板。
- 按需在 `interaction-spec/surfaces/<bounded-context>/<surface-id>.md` 为复杂或多 surface 记录职责、区域/槽位、领域对象、状态、动作、错误、权限、键盘焦点和 `traces_to`。
- 覆盖屏幕 / 组件地图、领域实体 / 状态 / 动作映射、用户路径、状态矩阵、E2E obligation、跨屏一致性体检。
- 生成主可操作原型时只呈现产品界面本身，不呈现阅读顺序、AC / trace、Flow / State 展板、reviewer 指引、manifest 说明或组件目录。
- 检查主原型和可视化资产的用户可见文字是否默认中文；例外项必须记录来源和理由。

</step>

<step id="step-2" n="2" goal="visual-interaction 资产 + manifest">

- standard / deep 档由 interaction-designer 委托 visual-interaction-design 子流程，基于 `interaction-spec/**` 的 affected surfaces 生成必要的 HTML / SVG variants 到 `visual-interaction/variants/**`。
- standard / deep 档生成 `visual-interaction/prototype/index.html`：作为唯一默认人类入口的高还原可操作前端页面，覆盖 P0 点击路径、关键状态和 desktop/mobile 主要视口；页面内不得出现阅读顺序、AC / trace、Flow / State 展板、reviewer 指引、manifest 说明或组件目录。
- light 档默认不生成可视化原型；若用户或 Gate 需要人类确认，再升级到 standard 档。
- 不默认生成 gallery、components、flows、states 等可见说明页面；需要补证据时写入 `visual-interaction/evidence/**`，不作为人类入口。
- 所有用户可见文字默认使用中文；允许保留的英文仅限品牌名、产品专名、代码标识、行业通用英文缩写或上游明确指定的外语文案。
- standard / deep 档调用 `harness evidence visual manifest --mission <mission-id> --json` 生成 `visual-interaction-manifest.json`。
- 在 interaction.md「原型合同与阅读顺序」段引用 `interaction-spec/`；standard / deep 档还要在「可视化交互资产」段引用 manifest、`prototype/index.html` 主入口与关键变体路径，并标明主原型是唯一默认人类入口。

</step>

<step id="step-3" n="3" goal="contract.yaml 初始化 + execution_result 写入">

- 若 `contracts/interaction.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage design --template interaction --json`。
- 调用 `harness contract add-execution-result --mission <mission-id> --stage design --role interaction-designer --json`。
- 调用 `harness contract patch`，把 artifact_tier / interaction_spec / surface_baseline / surface_changeset / prototype_interfaces / domain_model_coverage / flows / states / scenarios / validation_rules / consistency_report / obligations 从 interaction.md 与 `interaction-spec/**` 抽取写入 contract.yaml；standard / deep 档再写入 information_architecture / visual_artifacts。
- `traces_to` 必须命中 prd.contract.yaml AC / FR / NFR / delta spec Requirement / Scenario。

</step>

<step id="step-3a" n="3a" goal="PRD 回流检查">

- 对照 `product/product-definition.md`、`product/product-domain-model.md`、`prd.contract.yaml`，检查原型设计是否引入新的用户目标、AC、Scenario、领域实体、实体状态、用户动作、权限规则或范围变化。
- 如果只是把既有 PRD 内容表达为界面和状态，继续 reviewer 循环。
- 如果原型设计需要改变 PRD 阶段内容，停止 interaction 推进，将差异写入 interaction.md「PRD 回流检查」和 contract 的 open_questions / concerns，并发起 Decision Gate 或路由回 prd。
- 不得直接修改产品定义包或差量 spec。

</step>

<step id="step-4" n="4" goal="reviewer 循环">

最多 3 轮；本轮 `interaction-reviewer` 返回 PASS 时退出。

通过 `@interaction-reviewer` native delegation调用 `interaction-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）

Reviewer brief 必须包含：

- interaction.md、`interaction-spec/**`、`contracts/interaction.contract.yaml`。
- standard / deep 档或 workflow 要求视觉证据时，包含 `visual-interaction-manifest.json`、preview 入口、关键 HTML / SVG 变体。
- artifact tier 选择理由，以及该 tier 是否足以支撑下游实现和审查。
- standard / deep 档时，`prototype/index.html` 是否是主可操作原型入口，且未混入评审说明、AC / trace、Flow / State 展板和组件目录。
- 产品定义包、领域模型、delta specs、user_journey / frontend_ui obligations、上游约束摘要。
- 原型可见文案语言检查：用户可见文字默认中文，例外项必须有来源和理由。

每轮进入前调用：

```bash
harness contract patch --add-round --mission <mission-id> --stage design --review effectiveness --json
```

处理审查结论：

- HOLD / BLOCKED：修复 interaction.md / interaction-spec；standard / deep 档按需修复 variants / preview / manifest，记录本轮发现与修复，重新进入 reviewer 循环。
- PASS：调用 `harness contract patch --reviewer-verdict PASS --mission <mission-id> --stage design --json`，退出循环。
- 达到 3 轮仍有阻断：询问用户选择解决方向、接受降级 approval，或升级 BLOCKED。

</step>

<step id="step-5" n="5" goal="Artifact Gate 自检">

- 调用 `harness contract check --artifact contracts/interaction.contract.yaml --upstream prd.contract.yaml --upstream mission-contract.contract.yaml --json`。
- 调用 `harness interaction spec-check --mission <mission-id> --json`，验证 `interaction-spec/` 按 artifact tier 齐全，且 UI action / field / state / permission 可追溯到 domain model。
- standard / deep 档调用 `harness interaction visual-coverage-check --mission <mission-id> --json`，验证 visual manifest 覆盖 P0 flow、关键 state 和主要 viewport。
- standard / deep 档的 `visual-coverage-check` 必须同时验证主可操作原型存在、可静态识别交互 affordance，且主原型页面不包含评审/合同/覆盖说明类可见文案。
- 检查 `interaction-spec/interaction-contract.md` 或 `interaction-spec/checks.md` 是否已覆盖 copy language / 中文文案一致性；未解释的外语用户可见文案是 BLOCKER。
- 调用 `harness interaction locator-check --mission <mission-id> --json`，验证 P0/P1 scenario 已声明 data-testid 或 accessibility locator strategy。
- 调用 `harness alignment check --mission <mission-id> --stage interaction --json`，验证 UI surface / flow / state 对齐 PRD + domain model。
- 调用 `harness interaction gate run --mission <mission-id> --json`，聚合 spec-check、locator-check、alignment check，以及 standard / deep 档的 visual-coverage-check。

</step>

<step id="step-6" n="6" goal="Stage 完成 + Work Graph 输出">

- 调用 `harness mission stage complete interaction --mission <mission-id> --json`。`design-interaction-check-gate-pass` hook 会阻断缺少 gate PASS 报告的完成动作。
- 当前 lane action 产物 interaction.md + interaction-spec/，以及 standard / deep 档的 visual-interaction/，必须写入 lane_action.output_artifact / supplementary_artifacts，并在 contract YAML 的 `work_graph_artifact` 段引用同一路径。
- interaction.md 必须保留「沉淀候选」段：列出可复用原型模式、系统 surface 信息架构、领域对象到界面的映射、交互约束，以及是否应进入 project knowledge 或能力 spec。
- mission stage 的 interaction-spec 是本次 prototype project patch 证据，不是长期按任务堆积的系统原型库；standard / deep 档的 `prototype/index.html` 是本次 patch 的人类确认入口，不是把 spec 和 review 资料混排后的文档页。

</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `ui-trigger-false` | Step 0 返回 `requires_interaction=false` | 仅当上游明确 API-only / 无界面 / 纯后端 / CLI-only 时允许；返回 BLOCKED 并提示 skill-router 重新选择非 interaction lane |
| `prd-feedback-required` | Step 3a 发现原型需要改变 PRD / 领域模型 / AC / 范围 | 停止 interaction 推进，记录差异，发起 Decision Gate 或路由回 prd |
| `interaction-designer-blocked` | Step 1 返回 BLOCKED | missing_input 回 Step 0；scope_conflict 询问用户；decision_gate 暂停等待用户 |
| `visual-manifest-missing` | standard / deep 档 Step 2 manifest 失败 | 检查 variants；缺失则重新触发 visual-interaction-design，其它情况升级 BLOCKED |
| `interaction-spec-incomplete` | Step 5 gate 发现 `interaction-spec/` 按 artifact tier 缺失关键合同内容或 traceability | 回 Step 1 补齐 AI handoff 合同；不得只补 HTML 预览 |
| `reviewer-max-rounds` | Step 4 达到 max rounds | 进入用户 checkpoint |
| `gate-fail` | Step 5 `harness interaction gate run` FAIL | 按 failed_checks 回 Step 1 或 Step 2 修复 |

</failure_paths>

</workflow>
