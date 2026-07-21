# 可视化交互设计工作流

**Goal:** 根据产品定义、领域模型、interaction.md 和 interaction-spec/ 生成或归档可操作的高还原前端原型、交互设计变体和 reviewer 证据包。

**核心原则：**
- `visual-interaction/prototype/index.html` 是唯一默认人类入口，面向人确认，应尽量还原真实前端页面、真实导航层级、真实状态切换和关键点击路径。
- 下游 AI 的 canonical handoff 是按真实系统 surface 组织的 `interaction-spec/`；状态覆盖、截图、trace 和 manifest 只作为内部证据，不默认生成人类可见页面。
- 主可操作原型页面不得混入阅读顺序、AC / trace、Flow / State 展板、reviewer 指引、manifest 说明或组件目录。
- 不依赖 IDE 预览能力才能推进流程。
- 所有进入审查的设计变体必须有 manifest，且能追溯到 AC / Flow / State。
- 原型、HTML / SVG 变体和 preview 的用户可见文字默认必须使用中文；品牌名、产品专名、代码标识、行业通用英文缩写或上游明确指定的外语文案可保留原文，并在一致性体检中说明。

---

## 初始化

1. 读取 `harness-runtime/harness/stages/<mission-id>/interaction.md` 和 `interaction-spec/`（如果存在）。
2. 读取 `harness-runtime/harness/stages/<mission-id>/product/product-definition.md`、`product/product-domain-model.md`、`product/product-evidence.md` 和 `mission-contract.md`；如果 `solution.md` / `tech-design.md` 已存在，可以作为补充约束读取，但不得把它们作为 interaction 前置条件。
3. 调用 `harness-cli` 执行 `harness config snapshot --json`，读取 `visual_interaction` 策略摘要；不得直接读取 `harness-runtime/config/harness.yaml`。
4. 读取目标项目现有设计系统 / UI 约束，优先级：`project-context.md`、现有 `design-system/`、项目 CSS / Tailwind / shadcn theme、既有页面截图或组件。
5. 建立阶段目录：`harness-runtime/harness/stages/<mission-id>/visual-interaction/`，其中 `prototype/index.html` 放主可操作原型，`evidence/` 放按需生成的内部截图、状态覆盖和 reviewer 证据，`variants/` 放可纳入 manifest 的 HTML / SVG / CSS 设计资产。

---

## 执行

<workflow skill="visual-interaction-design" version="2">

<step n="1" goal="准备可视化设计 brief">
 - 从上游提取用户目标、AC、领域实体、领域状态、领域动作、关键 Flow、affected surfaces、信息架构、状态模型、错误 / 权限 / 空态 / loading 要求，以及用户可见文案语言策略。若 `interaction-spec/` 已存在，preview 必须以它的 surface-index / surface-changeset 为源，不得另造页面结构。
 - 从目标项目提取视觉约束：色彩 token、字体、spacing、组件库、圆角、表单 / 按钮 / 表格模式、已有页面布局密度。不得用外部生成器默认审美覆盖项目风格。
 - 写入 `visual-interaction/design-brief.md`，用于交互专家生成和维护设计资产。
 - brief 必须要求输出 `prototype/index.html` 作为唯一默认人类入口；它必须是高还原可操作前端页面，包含关键点击路径、表单/按钮/导航等真实交互 affordance，并声明 `role=operable_prototype`、覆盖的 Flow / State / viewport。
 - brief 不得默认要求输出 gallery、components、flows、states 等可见说明页面；如 Gate 或 reviewer 需要补证据，只写入 `evidence/`，且不作为人类入口。
 - 主原型的用户可见文字默认中文；风格必须继承目标项目现有设计系统，缺设计系统时才允许建立临时 design baseline。
</step>

<step n="2" goal="生成或导入设计变体">
 - 分支：产物来源
 - 情况：已有可导入 HTML / SVG / CSS 设计资产
 - 把外部生成目录中的 `*.html|*.svg|*.css` 作为 source，复制到 `visual-interaction/variants/`。
 - 外部工具只提供文件输入；Harness 的自动化链路只依赖归档后的 HTML / SVG / CSS、metadata 和 manifest。若外部资产与 `interaction-spec/` 不一致，或用户可见文字未按中文策略处理，以 `interaction-spec/` 为准重建 preview。
 - 情况：没有可导入资产
 - 由 interaction-designer / 主设计 Agent 按 brief 生成主可操作原型到 `visual-interaction/prototype/index.html`；所有用户可见文字默认中文。
 - 由 interaction-designer / 主设计 Agent 按 brief 生成 HTML / SVG 变体到 `visual-interaction/variants/`，用于补充状态图、流程图或方案对比；所有用户可见文字默认中文。
 - 按需生成 `visual-interaction/evidence/**` 作为内部审查证据；不得把它作为用户要打开的原型入口。
 - 主可操作原型必须至少覆盖 1 条 P0 happy path 和对应 loading / empty / error / permission 中适用状态；复杂 UI 推荐再提供 3 个方案变体或状态变体。
</step>

<step n="3" goal="生成 manifest">
 - 调用 `harness-cli` 运行 manifest 工具扫描并归档可视化资产：

 ```bash
 harness evidence visual manifest \
   --mission <mission-id> \
   --stage-dir harness-runtime/harness/stages/<mission-id>/visual-interaction \
	  --source-dir harness-runtime/harness/stages/<mission-id>/visual-interaction
 ```

 - 若从外部生成目录导入资产，把 `--source-dir` 指向该目录并加 `--copy`，将文件归档到 `visual-interaction/variants/`，再按 interaction-spec 生成本地主可操作原型。
 - 生成 `visual-interaction-manifest.json`，记录每个文件的 path、type、size、sha256、mtime、review_status、Flow / State / viewport 覆盖。
 - manifest 工具支持两种覆盖元数据来源：
 - HTML / SVG 注释：`<!-- harness: role=operable_prototype flows=FLOW-001 states=STATE-SUCCESS viewports=desktop,mobile ac=AC-01 -->`
 - 同名 sidecar：`<name>.harness.json` / `<name>.harness.yaml`
</step>

<step n="4" goal="更新 interaction.md">
 - 在 `interaction.md` 的「可视化交互资产」表中引用 manifest、`prototype/index.html` 主入口和关键变体路径。
 - 补齐每个 Flow / State 与变体的追溯关系。
 - 对主可操作原型写明：适用 viewport、覆盖状态、可点击路径、未覆盖状态和需要 E2E 的用户路径；对用户可见文案写明中文策略与例外项。
</step>

<step n="5" goal="交互审查brief">
 - 用 `spawn_agent` 调用 `interaction-reviewer` 时，brief必须包含：
 - interaction.md
 - interaction-spec/**
 - `visual-interaction-manifest.json`
 - `visual-interaction/prototype/index.html` 主可操作原型入口
 - 关键 HTML / SVG 变体
 - 产品定义 AC / Scenario
 - E2E obligation / data-testid / locator 清单
 - reviewer 只判断交互设计是否可实现、可验证、可追溯；不把“好看”作为 PASS 条件。
</step>

</workflow>

---

## HTML 资产管理规则

- HTML / SVG / CSS 是正式设计资产，必须进入 stage 目录并纳入 manifest。
- 主可操作原型必须从 `interaction-spec/` 派生，并保持像真实前端页面一样可点击、可检查、可截图；评审反馈先回写 `interaction-spec/` 和 `interaction.md`，再重建 prototype。
- `evidence/` 只存内部审查证据，不能替代主可操作原型；状态墙、组件目录、coverage、阅读顺序和 reviewer 指引不得出现在主原型页面。
- 资产必须包含覆盖元数据：HTML / SVG 注释或同名 sidecar 至少覆盖 Flow / State / viewport。
- interaction.md 改变时，交互专家必须同步更新对应设计资产和 manifest。
- 外部预览或生成工具不是 Harness Gate 前置条件；Gate 只检查阶段目录中的资产、manifest、contract 和 reviewer 结论。
