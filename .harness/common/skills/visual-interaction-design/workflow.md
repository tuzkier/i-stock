# 可视化交互设计工作流

**Goal:** 根据产品定义、领域模型、interaction.md 和 interaction-spec/ 生成或归档可操作的高还原前端原型、交互设计变体和 reviewer 证据包。

**核心原则：**
- 长期原型工程主入口是唯一默认人类入口，面向人确认，应尽量还原真实前端页面、真实导航层级、真实状态切换和关键点击路径。
- 下游 AI 的 canonical handoff 是按真实系统 surface 组织的 `interaction-spec/`；状态覆盖、截图、trace 和 manifest 只作为内部证据，不默认生成人类可见页面。
- 主可操作原型页面不得混入阅读顺序、验收追溯、Flow / State 展板、reviewer 指引、manifest 说明或组件目录。
- 不依赖 IDE 预览能力才能推进流程。
- 所有进入审查的设计变体必须有 manifest，且能追溯到验收场景 / Flow / State。
- 原型、HTML / SVG 变体和 preview 的用户可见文字默认必须使用中文；品牌名、产品专名、代码标识、行业通用英文缩写或上游明确指定的外语文案可保留原文，并在一致性体检中说明。

---

## 初始化

1. 读取 `harness-runtime/harness/artifacts/<mission-id>/interaction/interaction.md` 和 `interaction-spec/`（如果存在）。
2. 读取 `harness-runtime/harness/artifacts/<mission-id>/product/product-definition.md`、`product/product-domain-model.md`、`product/product-evidence.md` 和 `mission-contract.md`；如果 `solution.md` / `tech-design.md` 已存在，可以作为补充约束读取，但不得把它们作为 interaction 前置条件。
3. 调用 `harness-cli` 执行 `harness config snapshot --json`，读取 `visual_interaction` 策略摘要；不得直接读取 `harness-runtime/config/harness.yaml`。
4. 读取目标项目现有设计系统 / UI 约束，优先级：`project-context.md`、现有 `design-system/`、项目 CSS / Tailwind / shadcn theme、既有页面截图或组件。
5. 建立阶段目录：`harness-runtime/harness/artifacts/<mission-id>/interaction/visual-interaction/`，其中 `evidence/` 放按需生成的内部截图、状态覆盖和 reviewer 证据，`variants/` 放可纳入 manifest 的 HTML / SVG / CSS 设计资产；主可操作原型写入项目持有的独立原型工程目录（`prototype.interactive_prototype.prototype_project_root`，默认建议 `prototype/`，git 跟踪、随 Mission 分支隔离），不在 `project-knowledge/` 下、不在 mission artifact 下，也不写成每个 mission 一份的 artifact 副本。

---

## 执行

<workflow skill="visual-interaction-design" version="2">

<step n="1" goal="准备可视化设计 brief">
 - 从上游提取用户目标、验收场景 / 条件、领域实体、领域状态、领域动作、关键 Flow、affected surfaces、信息架构、状态模型、错误 / 权限 / 空态 / loading 要求，以及用户可见文案语言策略。若 `interaction-spec/` 已存在，preview 必须以 `interaction-spec/use-case-realization.md`、`interaction-spec/surface-model.md` 和 `interaction-spec/interaction-contract.md` 为源，不得另造页面结构。
 - 从目标项目提取视觉约束：色彩 token、字体、spacing、组件库、圆角、表单 / 按钮 / 表格模式、已有页面布局密度。不得用外部生成器默认审美覆盖项目风格。
 - 写入 `visual-interaction/design-brief.md`，用于交互专家生成和维护设计资产。
 - brief 必须要求输出长期原型工程主入口作为唯一默认人类入口；它必须是高还原可操作前端页面，包含关键点击路径、表单/按钮/导航等真实交互 affordance，并声明 `role=operable_prototype`、覆盖的 Flow / State / viewport。
 - brief 不得默认要求输出 gallery、components、flows、states 等可见说明页面；如 Gate 或 reviewer 需要补证据，只写入 `evidence/`，且不作为人类入口。
 - 主原型的用户可见文字默认中文；风格必须继承目标项目现有设计系统，缺设计系统时才允许建立临时 design baseline。
</step>

<step n="2" goal="生成或导入设计变体">
 - 分支：产物来源
 - 情况：已有可导入 HTML / SVG / CSS 设计资产
 - 把外部生成目录中的 `*.html|*.svg|*.css` 作为 source，复制到 `visual-interaction/variants/`。
 - 外部工具只提供文件输入；Harness 的自动化链路只依赖归档后的 HTML / SVG / CSS、metadata 和 manifest。若外部资产与 `interaction-spec/` 不一致，或用户可见文字未按中文策略处理，以 `interaction-spec/` 为准重建 preview。
 - 情况：没有可导入资产
 - 由 interaction-designer / 主设计 Agent 按 brief 生成或修改长期原型工程主入口；所有用户可见文字默认中文。
 - 由 interaction-designer / 主设计 Agent 按 brief 生成 HTML / SVG 变体到 `visual-interaction/variants/`，用于补充状态图、流程图或方案对比；所有用户可见文字默认中文。
 - 按需生成 `visual-interaction/evidence/**` 作为内部审查证据；不得把它作为用户要打开的原型入口。
 - 主可操作原型必须至少覆盖 1 条 P0 happy path 和对应 loading / empty / error / permission 中适用状态；复杂 UI 推荐再提供 3 个方案变体或状态变体。
</step>

<step n="3" goal="生成 manifest">
- 调用 `harness-cli` 运行 manifest 工具扫描长期原型工程主入口和阶段可视化资产：

 ```bash
 harness evidence visual manifest \
   --mission <mission-id> \
   --stage-dir harness-runtime/harness/artifacts/<mission-id>/interaction/visual-interaction \
   --source-dir <prototype_project_root> \
   --source-dir harness-runtime/harness/artifacts/<mission-id>/interaction/visual-interaction
 ```

 - 第一条 `--source-dir` 必须是 `harness config snapshot` 解析出的 `prototype.interactive_prototype.prototype_project_root`（默认建议 `prototype/`），不再默认指向 `project-knowledge/product/prototype/`。
 - 若从外部生成目录导入资产，额外传入该目录并加 `--copy`，将外部文件归档到 `visual-interaction/variants/`；主可操作原型仍必须按 interaction-spec 更新到独立原型工程目录。
 - 生成 `visual-interaction-manifest.json`，记录每个文件的 path、absolute_path、source、type、size、sha256、mtime、review_status，以及 trace 覆盖：surfaces / use_cases / objects / scenarios / flows / states / viewports。长期原型工程主入口必须通过 HTML 注释或 sidecar 声明 `role=operable_prototype`。
 - **两级锚点（trace 脊柱）**：
   - **页面级声明块**（每个原型页面文件顶部一条 harness 注释，是 manifest 的覆盖元数据来源，也是抗整页重写的存在性保证）：
     `<!-- harness: role=operable_prototype surf=SURF-002 suc=SUC-03,SUC-03-OP-01 obj=OBJ-01 scn=SCN-01 flows=FLOW-001 states=STATE-SUCCESS viewports=desktop,mobile -->`
   - **元素级 data 属性**（每个界面边界区域，供 trace-coverage-check 对账和 E2E 定位）：`data-surf="SURF-002"`、`data-suc="SUC-03-OP-01"`、`data-obj="OBJ-01"`，P0/P1 操作另带 `data-testid`。
   - **字段级 data 属性（全覆盖强制）**：在真正渲染业务对象字段的元素上加 `data-field="OBJ-02.status"`（对象限定、点号自描述、多值用空格 / 逗号分隔），落在对应 `data-obj` 区域内部。`contracts/interaction.contract.yaml#surface_bindings[].fields` 为每个绑定的 OBJ 声明必须可见的字段清单（如 `OBJ-02: [id, title, kind, stage, status]`，源自领域模型 + 验收场景）；trace-coverage-check 强制：被绑定的 OBJ 必须声明 fields（确无字段时显式 `fields: {OBJ-06: []}` 并在 surface-model 说明理由），声明的每个字段必须有对应 `data-field` 锚点，原型不得出现未声明的字段锚点。把"OBJ 被锚一次"升级为"OBJ 关键字段逐个被锚"。
     - **字段可见性决策规程（fields 怎么推出来，分母固定）**：fields 不是凭印象挑几个字段填。以**领域模型该 OBJ 的字段全集**为起点（分母），对每个字段二分类后落成 `fields` 声明：① 被某验收场景（`SCN-xx`）或某 PRD 流步骤引用 / 比较 / 操作 / 校验 → **必现**，进 `fields` 清单 + 原型打 `data-field`；② 纯内部 / 审计 / 主键派生 / 仅状态机内部用、用户任务中无需呈现 → **显式标不可见**：从 `fields` 清单剔除并在 surface-model 的领域到界面映射处逐个写明剔除理由（如"`OBJ-02.created_by` 仅审计，用户任务不需要"）。不允许"既没进必现清单、也没写不可见理由"的字段——那是覆盖分母被人为缩窄。
     - （建议后续加弱门：声明的 `fields` 必须 ⊆ 领域模型该 OBJ 的字段全集，且被验收场景 / 流步骤引用的字段不得缺席于 `fields`，防止人为缩窄覆盖分母绕过全覆盖。）
   - 三级锚点的 ID / 字段必须与 `contracts/interaction.contract.yaml#surface_bindings`（含 `fields`）一致；ID 引用上游真源（SURF/SUC/OBJ/SCN + OBJ 字段），不在原型里新造或改写。
   - **可视 trace 层（dev-only）**：把 `harness-runtime/templates/prototype/harness-trace-overlay.js` 放进 `prototype_project_root` 并在原型页面以开发态引入（`<script src="harness-trace-overlay.js" defer></script>`，相对路径，file:// 与本地服务器都可加载）。走查时按 `T` 或加 `?trace=1` 开关，叠加 SURF·SUC·OBJ badge + 侧栏汇总，让人直观看到每屏 / 每区域对应的设计归属；它只在 trace 模式注入，不污染生产 UI。
   - **原型框架 shell（用例 / 界面导航 + 内嵌原型，dev-only）**：把 `harness-runtime/templates/prototype/harness-prototype-frame.html` 放进 `prototype_project_root`。它是 Harness 自带的原型外层 shell —— 左栏分两组（数据源 `trace-nav.js` 由 `harness interaction trace-coverage-check --prototype-root <dir>` 生成）：「本任务聚焦 · 系统用例」= 当前 mission 的 SUC（含描述，来自 `use-case-model.md` 标题）；「项目界面 · Surface」= 项目级稳定界面 SUR-*（含描述 / 类型，来自 `project-knowledge/product/ui-surfaces/*.md`），按界面而非业务用例组织。每项标注是否本任务涉及、是否有可深链入口；右侧 `<iframe>` 内嵌真正的可操作主原型 `index.html`，点目录项按 `page_entry` 深链并高亮 `anchor_root`。它是导航/走查入口，**不是** operable / 人类确认入口（确认入口仍是干净的 `index.html`），不渲染产品 UI、不承载 trace 锚点；需通过本地静态服务器打开。这是 `trace-spine-forward-navigable` 不变式面向人的实现：正向选择落在 shell 层、不进主原型 UI（不违反 `operable-prototype-first`）。
 - manifest 工具支持两种覆盖元数据来源：上面的 HTML / SVG 注释（支持 `surf/suc/obj/scn` 简写或 `surfaces/use_cases/objects/scenarios` 全称），或同名 sidecar：`<name>.harness.json` / `<name>.harness.yaml`。
</step>

<step n="4" goal="更新 interaction.md">
 - 在 `interaction.md` 的「可视化交互资产」表中引用 manifest、长期原型工程主入口和关键变体路径。
 - 补齐每个 Flow / State 与变体的追溯关系。
 - 对主可操作原型写明：适用 viewport、覆盖状态、可点击路径、未覆盖状态和需要 E2E 的用户路径；对用户可见文案写明中文策略与例外项。
</step>

<step n="5" goal="交互审查brief">
 - 用 `spawn_agent` 调用 `interaction-reviewer` 时，brief必须包含：
 - interaction.md
 - interaction-spec/**
 - `visual-interaction-manifest.json`
 - 长期原型工程主可操作原型入口
 - 关键 HTML / SVG 变体
 - 产品定义验收场景 / 条件
 - E2E obligation / data-testid / locator 清单
 - reviewer 只判断交互设计是否可实现、可验证、可追溯；不把“好看”作为 PASS 条件。
</step>

</workflow>

---

## HTML 资产管理规则

- HTML / SVG / CSS 设计变体和内部证据必须进入 stage 目录并纳入 manifest；长期原型工程中的主可操作原型不复制进 stage 目录，但必须纳入 manifest。
- 主可操作原型必须从 `interaction-spec/` 派生，并保持像真实前端页面一样可点击、可检查、可截图；评审反馈先回写 `interaction-spec/` 和 `interaction.md`，再重建 prototype。
- `evidence/` 只存内部审查证据，不能替代主可操作原型；状态墙、组件目录、coverage、阅读顺序和 reviewer 指引不得出现在主原型页面。
- 资产必须包含覆盖元数据：HTML / SVG 注释或同名 sidecar 至少覆盖 Flow / State / viewport。
- interaction.md 改变时，交互专家必须同步更新对应设计资产和 manifest。
- 外部预览或生成工具不是 Harness Gate 前置条件；Gate 只检查阶段目录中的资产、manifest、contract 和 reviewer 结论。
# visual-interaction-design / references

本目录存放 **visual-interaction-design skill 产出"可视化设计证据"时引用的框架级规范与模板**。当前为空——按需补，不必铺满。

## 装什么

面向长期原型工程主入口、`visual-interaction/variants/`、`visual-interaction/evidence/`、`visual-interaction-manifest.json`、`design-brief.md` 这一组资产的产出过程，例如：

- **variant 命名 / 目录布局规范**：variant id、surface、viewport、device frame、对应 interaction-spec surface 的引用约定
- **prototype 信息架构范式**：长期原型工程中主可操作原型的目录布局、边界和最小覆盖
- **manifest 语义说明**：解释 `harness evidence visual manifest` 命令生成的字段含义（实际 schema 由 CLI 强制，本目录只做语义注释与最小示例）
- **design-brief 模板**：怎么从 product-definition / interaction-spec 提取交互专家所需的上下文（领域对象、状态、权限、动作、E2E obligation、关键约束）
- **可访问性可视证据规范**：对比度、focus ring、视口覆盖（mobile / tablet / desktop）、暗色模式 / RTL 的截图义务
- **既有风格引用约定**：怎么引用项目现有 CSS / design token，而不是另起一套——区别于 OD 把 design-system 注入 `:root`

## 不装什么

- **HTML seed / paste-ready layout / 通用设计 token 库**——Harness 的可视化资产是**设计证据**，不是终态交付，不需要框架自带 HTML 物料库（详见下节 "与 Open Design 的区别"）。
- **结构化原型合同骨架（state matrix / flow pattern / interaction-spec schema）**——那是 [interaction/references/](../../interaction/references/README.md) 的工作面。
- **项目自身的具体视觉资产 / 实际 variants / preview HTML**——产出于 `harness-runtime/harness/artifacts/<id>/interaction/visual-interaction/`，不进入框架资产库。
- **品牌 / 视觉 token 套件**——项目的视觉 token 走项目仓库自己的源码或 `project-knowledge/`，不在框架层维护"129 套 design-system"这种物料库。

## 与 Open Design (`nexu-io/open-design`) `design-templates/` + `design-systems/` 的区别

| | OD | 本目录 |
|---|---|---|
| HTML / preview 地位 | 终态交付，给最终用户看 | 长期原型工程主入口是唯一默认人类确认入口；`visual-interaction/` 内部证据受 manifest / Gate 约束，AI handoff 仍以 interaction-spec 为准 |
| 物料库形态 | 框架自带 80+ HTML 模板 + 129 套 design-system token | 不维护通用 HTML 模板和 token 库；引用项目自有风格 |
| 资产形态 | `template.html` seed + `layouts.md` + `checklist.md` + design-system tokens | manifest 字段语义 / 命名约定 / 主可操作原型信息架构 / a11y 视觉证据规范（纯文本/markdown） |
| 验证手段 | 五维 critique 自检后直接 emit `artifact` | reviewer 循环（interaction-reviewer）+ Artifact Gate + E2E obligation |

OD 把 HTML 当成熟产品；Harness 把 HTML 当成"用来证明合同被正确承载"的证据，所以本目录立的是**证据规范**，不是物料库。

## 三层资产关系

```
框架级规范（本目录）
   │   被 visual-interaction-design workflow 引用
   ▼
项目级视觉约定（项目自有 CSS / token / project-knowledge/）
   │   各项目自己维护
   ▼
本次 mission 设计证据（harness-runtime/harness/artifacts/<id>/interaction/visual-interaction/）
   │   variants / preview / manifest / design-brief
   ▼
被 interaction-reviewer + Artifact Gate 审查
```

## 与 interaction/references/ 的边界

- **interaction/references/**：合同骨架（"原型该怎么写"）
- **本目录**：证据规范（"原型变体与 preview 怎么落地、命名、组织、归档"）
- 同一 pattern 若两边都需要，统一沉到 interaction/references/，本目录只引用。

## 维护提示

- 新增规范命名 kebab-case，每个规范一个 `.md`，开头一句话写"何时引用"。
- 涉及 CLI 字段语义的，注明对应 `harness evidence visual` 子命令版本，CLI 变更时同步更新。
- 不要把项目特有的视觉风格沉到这里——那是项目自己的事。
