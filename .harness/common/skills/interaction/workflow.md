# 交互阶段动作工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §4（状态矩阵、错误路径、可访问性）+ `.harness/docs/workflow-authoring.md` + `visual-interaction-design` 子流程
> **设计原则**：见同目录 `SKILL.md` 的"设计原则"段；本工作流的不变式表是这些原则的可执行落点。

下文出现的所有 `harness ...` 命令一律通过 harness-cli 技能调用。

<workflow stage="interaction" version="2">

<goal>
从产品定义阶段产出的产品定义包、用例模型（含状态枚举：业务态/纯UI态）、系统行为描述、验收场景、领域模型、差量规格和任务契约出发，按 `control_plane.stage=interaction` 在方案阶段之前把行为转成可走查的**行为图**。阶段重心 = **2 手写真相源 + 3 机器生成视图**：`interaction.md`（阶段入口）+ `interaction-spec/surface-model.md`（容器轴 + surface 目录机器段）+ `interaction-spec/behavior-graph.yaml`（**SSOT**：page_states 节点 / steps 拍 / edges 转移 / flows 路径）；`interaction-spec/views/by-suc|by-surface|by-object.md` 由 `harness interaction project` 从行为图**生成、禁止手写**。覆盖颗粒下沉到 step（流步骤×结局）/ page-state；flow 与 state 多对多、不得等同。主可操作原型在独立原型工程目录持续迭代（`prototype.interactive_prototype.prototype_project_root`，默认 `prototype/`，git 跟踪、随分支隔离），按 R1–R8（见 `prototype-standard.md`）实现——先有布局骨架（区域树）再写 HTML（compose-before-HTML），锚点 `data-step`/`data-pagestate`/`data-via`/`data-region` 内联。唯一 lint 是 `harness interaction prototype-check`（一次对账）。原型阶段完成前必须有人类在走查驾驶舱以 operation-walk 走查确认，审查员 PASS 不能替代用户确认。
</goal>

<role>
你是原型交互设计者，先从产品定义的业务用例、系统用例、系统行为描述、界面承载要求和验收场景建立用例实现基线，再从产品定义和领域模型推导系统界面边界、领域对象、领域命令、状态、权限和业务反馈，最后才生成可视化资产。所有界面边界、路径和状态必须可追溯到已确认系统行为、系统用例、验收场景 / 条件和领域对象，并可被端到端定位器定位。
</role>

<stage_capability>

交互阶段对应 RUP 需求工作流中的用例流细化，以及分析与设计中的用例实现 / 界面原型。它的核心能力不是生成更多交互文档，而是回答“用户如何通过界面完成已确认系统用例”。

| 能力 | 判断问题 | 产物要求 |
|---|---|---|
| 输入合格性判断 | 产品定义包是否已经给出已确认系统用例、系统行为描述、主成功流、备选流、异常流、状态枚举（业务态/纯UI态）、界面承载要求、验收场景 / 条件和领域对象。 | 在 `interaction.md#输入就绪` 写清输入就绪检查；输入不足时回流产品定义或决策门，不在交互阶段补造用户目标、系统行为或验收场景。 |
| 用例实现判断 | 每个需要界面承载的系统用例、`SUC-xx-FLOW-xx` 流步骤和 `SUC-xx-OP-xx` 系统操作是否能转成用户动作、系统反馈、关键状态、恢复路径和验证义务。 | 建立系统用例到交互实现矩阵和系统操作覆盖与自洽校验；不得用页面清单、组件清单或视觉稿反推用户路径。 |
| 界面承载判断 | 本次是创建、修改、扩展还是废弃哪些真实系统界面边界；是否会产生重复入口或信息架构漂移。 | 在 `surface-model.md` 写清界面边界、基线引用、信息架构和领域到界面映射；缺少基线时说明证据和处理。 |
| 路径状态判断 | 主成功流、备选流、异常流、空态、加载、错误、权限、禁用、键盘焦点和恢复路径是否被 page-state 承载、被 edge 连成可走查路径。 | 在 `behavior-graph.yaml` 的 page_states/steps/edges/flows 写清；每个结局态有锚点且 operation-walk 可达，否则 prototype-check 不 PASS。 |
| 验证义务判断 | 用户可观察结果是否能被端到端、组件、可访问性、人工证据或已接受替代方案证明。 | 为 P0 / P1 用户路径声明定位器或可访问性策略，并把验证义务交给后续执行、代码审查和验证阶段。 |
| 产品定义回流判断 | 交互设计是否暴露了需要新增或修改系统行为、用户目标、用例流、验收场景、领域状态、权限规则或范围的问题。 | 将差异写入回流检查；不得直接修改产品定义包或静默扩大范围。 |

</stage_capability>

<invariants>

| 编号 | 检查 | 执行位置 |
|---|---|---|
| `visual-manifest-via-cli` | `visual-interaction-manifest.json` 不得被智能体直接写入或编辑，必须经命令行生成 | `design.interaction` 覆盖层禁止 `Write(**/visual-interaction-manifest.json)` |
| `reviewer-readonly` | `interaction-reviewer` 必须在只读子 Agent 中调用 | 子 Agent 注册表 `readonly=true` |
| `webfetch-via-ask` | WebFetch / WebSearch 走询问通道 | `design.interaction` 覆盖层询问 |
| `fix-then-recheck` | `interaction.md` 修改后必须重新过审查员 | `design-interaction-check-pending-recheck` 钩子 |
| `prd-feedback-gate` | 原型设计若需要新增或修改系统行为描述、验收场景 / 条件、用户旅程、领域模型或范围，必须回流产品定义阶段或决策门 | 步骤 3a |
| `behavior-graph-first` | 必须先把系统用例 / 流 / 结局态建成 behavior-graph（page_states/steps/edges/flows），再设计或修改原型；不得从页面清单倒推用户路径 | 步骤 0 / 步骤 1 |
| `surface-iteration-supersede` | 迭代既有沉淀 surface 时按"身份是否延续"选 modify/extend（沿用 id）或 `supersede`（换代、旧 id→新后继）；不得用 keep 叠加出两个并存界面、也不得用 retire 把有后继的能力当无后继删。supersede 必须在 `behavior-graph.yaml` 顶层声明 `superseded:`（含真实存在且被覆盖的 `successor`），否则 `prototype-check` `SUPERSEDE_SUCCESSOR_MISSING` FAIL | 步骤 1 / 步骤 4 |
| `prd-readiness-for-interaction` | 产品定义必须提供已确认系统用例、系统行为描述、主成功流、备选流、异常流、界面承载要求和可执行验收场景 / 条件；缺口回流产品定义阶段 | 步骤 0 |
| `interaction-spec-canonical` | 手写真相源只有 `interaction-spec/surface-model.md`（容器轴）+ `interaction-spec/behavior-graph.yaml`（SSOT）；`views/by-suc\|by-surface\|by-object.md` 由 `harness interaction project` 生成、禁止手写；需要人类确认时长期原型工程主入口是唯一默认人类入口 | 步骤 1 / 步骤 2 |
| `surface-first-prototype` | `interaction-spec/surface-model.md` 必须按真实系统界面边界组织，并含 CLI 可解析的「surface 目录机器段」 | 步骤 1 |
| `trace-spine-forward-navigable` | trace 脊柱必须正向可导航：给定 SUC/OBJ/step 能经 `harness interaction resolve-feedback`（消费 `behavior-graph.yaml`）解析出承载它的 page_state(s) + `page_entry` + `anchor_root`；正向跳转入口不得做进主可操作原型页面 | 步骤 3 / 步骤 5 |
| `prototype-project-patch` | 长期原型视为原型工程；本次手写真相源是增量变更合同；主可操作原型在独立原型工程目录内持续迭代，不能每个 mission 在 artifact 下另建主原型副本 | 步骤 2 / 步骤 6 |
| `prototype-visible-copy-zh-cn` | 原型、HTML / SVG 变体、低保真 ASCII 线框和预览中的用户可见文字默认必须使用中文（ASCII 线框的占位标签同样用中文） | 步骤 1 / 步骤 2 / 步骤 4 |
| `operable-prototype-first` | 独立原型工程目录中的主入口必须是高还原、可操作页面；评审说明、验收场景 / 追溯、路径 / 状态展板和组件目录不得混入主原型页面 | 步骤 2 / 步骤 5 |
| `human-confirmation-required` | 原型阶段完成前必须获得用户对主可操作原型的明确确认；确认 FAIL 时回到同一独立原型工程目录继续修改并重新审查 | 步骤 5a / 步骤 6 |

</invariants>

<entry>

- 任务切片 `control_plane.stage=interaction`。
- **每个 mission 默认进入本阶段**（不再由 PRD 用例模型 `UIC-xx` 前置门控）。进入后由 step-0 的原型必要性判断决定是做完整原型还是判否跳过——判断是本阶段的第一职责，不是进入前提。
- 产品定义阶段已产出可供交互消费的业务用例、系统边界、已确认系统用例、系统行为描述、验收场景和领域模型；needed=true 时若只有功能列表或页面想法（缺已确认系统用例），在 step-0 输入合格性判断处回流产品定义阶段。

</entry>

<exit>

- `interaction.md` 写入设计阶段工作树，且含「设计意图」一节（视觉方向 / 主角强调 / 关键 OBJ 真实内容样例 / 参考 / 非目标）。
- `visual-interaction/variants/**` 含每个关键 surface 的低保真 ASCII 线框（区域树的人类可读文本渲染，如 `lowfi-wireframes.md`），与设计意图一并供 step-5a 呈现给用户。
- `interaction-spec/surface-model.md` 写入容器轴：界面边界、基线判断、信息架构 + **surface 目录机器段** + **布局骨架机器段（区域树·组成轴）**。
- `interaction-spec/behavior-graph.yaml` 写入 SSOT：page_states（objects[].region 落区 / placements）/ steps / edges / flows（带 rationale）。
- `interaction-spec/views/by-suc|by-surface|by-object.md` 由 `harness interaction project` 生成（带 GENERATED 头，未手写）。
- `contracts/interaction.contract.yaml` 已填充且 `harness contract check` PASS。
- `visual-interaction/visual-interaction-manifest.json` 由 `harness evidence visual manifest` 生成（提供 viewport 覆盖）。
- 独立原型工程中的主可操作原型存在并按 R1–R8 实现（含布局骨架 / 区域落区 / `data-region`）；`walkthrough.js` 已由 `harness interaction project` 生成。
- `harness interaction prototype-check` 通过（无 graph/reachability/anchor/coverage/composition 类 FAIL；viewport/upstream 类 WARN 可接受并说明）。
- `interaction-reviewer` 在等同严格度下通过；或卡死后用户在 Decision Gate 上显式拥有残留风险的 approval 已记录（审查循环本身永不因轮次自动放行）。
- 用户原型确认通过，确认记录写入 `harness-runtime/harness/traces/{mission_id}/user-prototype-confirmation.md` 并通过 `harness approval append --type checkpoint --stage interaction` 记录。
- `harness interaction gate run` 返回 `status=pass`，且对齐检查通过。

</exit>

<subagents>

| 角色 | 模式 | 范围 / 限制 | 包 |
|---|---|---|---|
| `interaction-designer` | spawn | 可写 `interaction.md`、`interaction-spec/surface-model.md`、`interaction-spec/behavior-graph.yaml`、独立原型工程目录、`visual-interaction/variants|evidence/**`、`design-brief.md`；**不得手写 `interaction-spec/views/**`**（由 `harness interaction project` 生成）；不得把主原型写成每 mission 一份的 artifact 副本 | `.harness/common/agents/interaction-designer.md` |
| `interaction-reviewer` | spawn readonly | 禁止 Edit / Write / MultiEdit / NotebookEdit / Bash | `.harness/common/agents/interaction-reviewer.md` |

</subagents>

<inputs>

| 引用 | 是否必需 | 平面 |
|---|---|---|
| `product/product-definition.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `product/product-domain-model.md` | true | Memory |
| `product/use-case-model.md` | true | Memory |
| `product/acceptance-scenarios.md` | true | Evidence |
| `mission-contract.md` | true | Intent |
| `project-context.md` | conditional: brownfield | Context |
| `project-knowledge/specs/_index.md` | conditional: `spec.enabled=true` | Memory |
| `project-knowledge/engineering/patterns/README.md` | conditional | Memory |
| `project-knowledge/design/decisions/README.md` | conditional | Memory |
| `project-knowledge/product/workflows/README.md` | conditional | Memory |
| `project-knowledge/product/ui-surfaces/README.md` | conditional | Memory |
| `project-knowledge/product/ui-design-system.md`（+ `design-system/` 分层） | conditional: 迭代系统 / 有既有界面 | Memory（设计系统：原则/框架/基础组件/业务组件/规范，装配 + 组成轴必读） |
| `project-knowledge/product/system-use-cases/behavior-graph.yaml` | conditional: 迭代系统 | Memory（项目级累积图，含 `surfaces` + `regions` 区域树基线） |
| `harness.yaml` | true via `harness config snapshot` | Memory |

</inputs>

<outputs>

| 产物 | 路径 | 类型 | 平面 / 校验器 |
|---|---|---|---|
| `interaction-md` | `harness-runtime/harness/artifacts/${mission-id}/interaction/interaction.md` | markdown | Memory |
| `surface-model` | `harness-runtime/harness/artifacts/${mission-id}/interaction/interaction-spec/surface-model.md` | 容器轴 + surface 目录机器段（手写） | Memory |
| `behavior-graph` | `harness-runtime/harness/artifacts/${mission-id}/interaction/interaction-spec/behavior-graph.yaml` | SSOT：page_states/steps/edges/flows（手写） | Memory |
| `views` | `harness-runtime/harness/artifacts/${mission-id}/interaction/interaction-spec/views/by-suc\|by-surface\|by-object.md` | 由 `harness interaction project` 生成（禁手写） | Memory |
| `interaction-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/interaction.contract.yaml` | 契约 | `harness contract check --upstream prd.contract.yaml --upstream mission-contract.contract.yaml` |
| `prototype-project-patch` | `prototype_project_root`（默认 `prototype/`；由 `harness config snapshot` 解析） | 可操作原型 | Memory + Evidence |
| `visual-manifest` | `harness-runtime/harness/artifacts/${mission-id}/interaction/visual-interaction/visual-interaction-manifest.json` | 清单 | 证据；引用长期原型工程主入口 |
| `user-prototype-confirmation` | `harness-runtime/harness/traces/${mission-id}/user-prototype-confirmation.md` | 人类确认记录 | Evidence |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化 + delivery_mode 判断 + 原型必要性判断（默认进入、阶段内判定）">

- 调用 `harness mission stage start --mission <mission-id> --stage interaction --json`。
- 调用 `harness trace log-init --mission <mission-id> --stage interaction --json`。
- 调用 `harness config snapshot --json`，读取阶段策略、模型路由、规格开关、交互门禁配置和 `prototype.delivery_mode`。
- 若 `prototype.delivery_mode=frontend_engineering`：返回路由错误给 skill-router，请求改派 `prototype-as-frontend` 技能；本技能不处理该路线。仅在 `prototype.delivery_mode=interactive_prototype`（默认）时继续。
- 调用 `harness frame current --mission <mission-id> --json`，校验 `mission_slice.control_plane.stage=interaction`。

**原型必要性判断（本阶段第一职责——每个 mission 默认进入到这一步，由这里判要不要原型）**

判定模型：**不再用 PRD 用例模型的 `UIC-xx` 前置门控**（该机制已退役）。每个 mission 都默认进入 interaction 阶段，由 interaction-designer 在此做一次轻量判断：**本任务是否存在用户可观察界面 / 用户旅程**。

- 读取 `mission-contract.md` + `product/product-definition.md`（及 `use-case-model.md`、`acceptance-scenarios.md` 如存在），直接判断：
  - **能明确判的自动判**：纯后端 / 接口 / 数据迁移 / 配置 / 脚本 / 纯命令行 / 重构等无用户可观察界面 → **判否**；明显有用户操作界面、页面、用户旅程、可视化展示 → **判是**。
  - **只有灰色地带（拿不准是否需要界面承载）才 `AskUserQuestion` 问用户**「这个任务需要设计原型 / 界面吗」；运行时不支持结构化提问时降级自然语言确认。不得静默假设。
- 把判定结论写入确定记录 `harness-runtime/harness/artifacts/<mission-id>/interaction/prototype-necessity.json`：
  ```json
  {"needed": false, "reason": "纯后端批处理，无用户可观察界面", "decided_by": "agent"}
  ```
  `needed`：true/false；`reason`：一句话依据；`decided_by`：`agent`（自动判）或 `user`（灰色地带问得）。
- **判否（needed=false）→ 跳过本阶段**：只写上述确定记录，**不产出 `interaction.md` / `interaction-spec/**` / 原型 / behavior-graph**；调 `harness trace log-step`（记录跳过与理由）后，按 board-router 以「interaction 无 output_artifact」推进到下一阶段（solution）。确定记录是本次跳过的合法性凭证（防止「漏做 interaction」被误当跳过）。本阶段在此结束，不进入 step-1。
- **判是（needed=true）→ 继续完整流程**：写确定记录（needed=true）后继续下列就绪准备与 step-1。

**（仅 needed=true 时执行）原型就绪准备 + 输入合格性判断**

- 解析独立原型工程目录：从 `harness config snapshot --json` 读取 `prototype.interactive_prototype.prototype_project_root`（及 `_status`）。
  - `prototype_project_root_status=resolved`：用该目录作为独立原型工程目录与 baseline 来源。
  - `prototype_project_root_status=unresolved`：向用户确认要使用的目录（推荐默认 `prototype/`），并把决定回写 `project-knowledge/engineering/policies/stage-rules.yaml` 的 `interaction.prototype_project_root`，再继续；不得擅自在 `project-knowledge/product/prototype/` 下迭代主原型。
  - baseline 来自当前 main 分支上的该目录（已累积的完整原型）；本次改动在 Mission 分支上对同一目录原地迭代，由分支隔离，验收合并即晋升。原型的 provenance 由该目录 git log 提供，不在 `project-knowledge/` 下另立台账。
- **组成基线纳入（迭代系统必做）**：读项目级累积图 `project-knowledge/product/system-use-cases/behavior-graph.yaml` 的 `surfaces` + `regions`（既有 surface 的区域树）、既有原型的 `data-region` 结构、设计系统基线 `project-knowledge/product/ui-design-system.md`。改 / 扩既有 surface 时**继承既有区域树与设计语言、不重造骨架**；新建 surface 从 `references/layout-patterns/` 选基底 pattern。缺设计系统基线又有既有界面时，先按 init 模板补 `ui-design-system.md` 或返回 BLOCKED，不在无基线下自由发挥布局。
- 调用 `harness context check --json`；PASS 则读 `project-context.md`。
- 读取 `product/use-case-model.md`、`product/acceptance-scenarios.md`、`product/product-definition.md`、`product/product-domain-model.md`，做交互输入合格性判断：
  - 必须存在已确认系统用例，不得只有业务用例或功能清单。
  - 每个需要界面承载的系统用例必须有参与者、目标、前置条件、触发、主成功流、备选流、异常流、后置结果。
  - 每个需要界面承载的系统用例必须能指向 `SUC-xx-FLOW-xx` 和 `SUC-xx-OP-xx`：触发、目标系统操作、对象 / 状态迁移 / 规则和可观察结果。
  - 每个需要界面承载的系统用例必须能指向界面承载要求：用户任务、必需展示信息、必需输入 / 操作、状态 / 错误 / 权限 / 反馈要求。
  - 每个 P0 / P1 系统用例必须能指向可执行验收场景 / 条件。
  - 任一缺口会导致交互阶段只能自行发明用户路径时，停止推进并回流产品定义阶段或决策门。

</step>

<step id="step-1" n="1" goal="interaction-designer 调度 + interaction.md 起草">

<dispatch role="interaction-designer" mode="spawn" />

任务信封必须包含：

- 任务目标。
- 输入路径和已读摘要：产品定义包、用例模型、验收场景、任务契约、`project-context.md`、相关差量规格、长期规格 / 模式 / 决策 / 原型工程 / 界面边界索引摘要。
- 输出路径：`interaction.md`、`interaction-spec/surface-model.md`、`interaction-spec/behavior-graph.yaml`、独立原型工程目录（`prototype_project_root`，默认 `prototype/`）中的主可操作原型；证据补充写 `visual-interaction/variants|evidence/**`、`design-brief.md`。**不要手写 `interaction-spec/views/**`**（由 `harness interaction project` 生成）。
- `interaction-spec/` 手写的只有 `surface-model.md` + `behavior-graph.yaml`；不得生成其它手写规格文件。额外证据写入 `visual-interaction/evidence/**`。
- 写入范围：仅限交互阶段主产物、智能体交接原型合同和可视化交互资产。
- 完成条件：交互分析方法与编号约定、用例实现矩阵、系统操作覆盖与自洽校验、受影响界面边界清单、既有界面基线、原型增量变更、界面边界变更清单、领域模型覆盖、领域命令到界面动作映射、状态矩阵、权限路径、智能体交接规格、验证义务、原型可见文案默认中文、长期原型工程主可操作原型和可视化资产引用。

interaction-designer 必须完成：

- 先建立用例实现矩阵：把每个需要界面承载的系统用例、`SUC-xx-FLOW-xx` 流步骤和 `SUC-xx-OP-xx` 系统操作映射到参与者、用户目标、主成功流、备选流、异常流、界面边界、关键状态、反馈、验收场景 / 条件和端到端验证义务。
- 对每条 `SUC-xx-FLOW-xx` / `SUC-xx-OP-xx` 做系统操作覆盖与自洽校验：交互可以补充用户动作、界面状态、反馈和验证义务，但不得新增、删除或改写目标系统操作；有差异时进入产品定义回流检查。
- 用例实现矩阵未成立前不得开始界面边界 / 原型设计；不得用页面清单反推用户路径。
- 在手写真相源中写清本次采用的分析顺序、编号规则、填写约定、操作判定和质量体检模板。
- 判断本次原型操作类型：`create_surface`、`modify_surface`、`extend_surface`、`retire_surface`、`supersede_surface`（**迭代取代**：把既有沉淀 surface/锚点换代成改名 / 换结构的后继，前驱覆盖由后继承接，详见 `prototype-standard.md`「迭代既有 surface 的四招」）或组合。**迭代既有界面时按"身份是否延续"先判 modify/extend（语义连续、沿用同一批 id）还是 supersede（语义换代、旧 id→新后继 id）**：不要 keep 硬留旧面再叠加新面（撞出两个并存界面，正是要避免的乱），也不要 retire 把有后继的能力当无后继删（丢血缘）。选 supersede 时在 `behavior-graph.yaml` 顶层写 `superseded:`（`predecessor` / `successor` / `kind` / 可选 `anchor_map` / `rationale`），前驱锚点会从合并图丢弃、原型只留后继一个面；`prototype-check` 强制后继真实存在且被覆盖（`SUPERSEDE_SUCCESSOR_MISSING` FAIL 防"假取代真删除"）。
- 修改既有界面时引用既有界面边界基线；不得生成孤立新页面。
- 产出 `surface-model.md`（容器轴 + surface 目录机器段 + **布局骨架机器段·区域树**）和 `behavior-graph.yaml`（SSOT：page_states/steps/edges/flows）作为手写真相源，再跑 `harness interaction project` 生成 `views/`。
- **先写设计意图（design intent，先于组成轴与 HTML）**：在 `interaction.md` 写一节「设计意图」，把下游"该长成什么样"显式钉住，作为 designer 自己要打中的靶子、reviewer 表达对照的依据、用户确认时一并查看的方向说明。它不另立 `interaction-spec/` 文件（包边界不变），就放在 `interaction.md`。至少覆盖：
  - **视觉方向 / 气质**：密度、语气、节奏——引 `design-system/principles.md` 的气质坐标；新项目无基线时就地确立一版或问用户，不留空猜。
  - **每个关键 surface 的主角与强调**：一句话"这屏主角是 X，用户一眼应先看到 Y"，对应区域树的优先级 / 扫描序意图（骨架槽位 ≠ 视觉层级，必须显式说强调谁）。
  - **关键对象真实内容样例**：每个关键 `OBJ-xx` 给一组**真实示例值**（非 lorem / 非占位），假数据会把布局与密度带歪。
  - **参考**：参考产品 / 截图 / 既有界面（如有，引来源）；**非目标**：明确不做成什么样，挡住自由发挥。
  - 无来源（用户未给方向 / 无既有基线）时**主动问用户**取这些方向，不静默自行发明——这正是过去偏差的高发口。
- **组成轴（compose-before-HTML，先于写 HTML）**：把信息架构落成每个 surface 的区域树（区域 × 嵌套 × 排布 × 优先级 × 角色 × 扫描序）写入 surface-model「布局骨架机器段」——新建从 `references/layout-patterns/` 选基底 pattern、改/扩继承累积图 `regions` 既有区域树、贴合 `ui-design-system.md`；再把 page_state 每个可见对象用 `objects[].region` 落区、非 OBJ 内容用 `placements` 落区。对象无法落到任何合理区域时返回 BLOCKED，不得硬堆。
- **从组件库装配（紧接组成轴）**：surface 挂在 `design-system/interaction-framework.md` 的应用外壳里；区域里放**业务组件**——先查 `design-system/business-components.md`，有则复用，无则定义新业务组件（绑上游 `SUC-xx`/`OBJ-xx`、由 `base-components.md` 的 `BC-*` 组成、列全状态矩阵）；业务组件由基础组件搭、全用 `design-spec.md` 登记 token。原型不从裸 HTML 堆控件。本次新定义的业务组件写进 `business-components.md` + 实现于 `prototype/components/business/`。
- 行为图必须覆盖来源追溯、每个 SUC 每条 flow 每个结局的拍、ENTRY 起的连边、领域字段级映射（page_state.objects，**含 region 落区**）、验收追溯（step.acceptance_refs）；不得把多结局压进散文。
- 不按复杂度拆分额外规格文件。手写内容收敛在 `surface-model.md` + `behavior-graph.yaml`；`views/` 由 `harness interaction project` 生成、不手写。
- 覆盖屏幕 / 组件地图、领域实体 / 状态 / 动作映射、用户路径、状态矩阵、端到端验证义务、跨屏一致性体检。
- 生成或修改主可操作原型时，必须在独立原型工程目录（`prototype_project_root`）内持续迭代，只呈现产品界面本身，不呈现阅读顺序、验收场景 / 追溯、路径 / 状态展板、审查员指引、资产清单说明或组件目录。
- 必须按行为图、区域树与设计系统植入锚点：态容器 `data-pagestate="PS-…"`、触发拍的控件/容器 `data-step="SUC-…-FLOW-….<state>"`、系统事件诱发控件 `data-via="<surf>/<控件>"`、**区域容器 `data-region="R-…"`**、**应用外壳容器 `data-shell="SHELL-…"`**、**业务组件实例 `data-bizcomp="UC-…"`**、E2E 边控件 `data-testid`；任一时刻只一个激活 `data-pagestate`（带 `[data-active]`）；每个承载内容的区域必须有 `data-region` 元素（与四方锚点同构）。ID 引用 behavior-graph / 区域树 / 设计系统目录，不新造或改写。
- 检查主原型和可视化资产的用户可见文字是否默认中文；例外项必须记录来源和理由。

</step>

<step id="step-2" n="2" goal="独立原型工程迭代 + 可视化交互资产 + 资产清单">

- 由 `interaction-designer` 委托 `visual-interaction-design` 子流程，基于 `surface-model.md` 的受影响界面边界**和布局骨架区域树**、`behavior-graph.yaml` 的 page_states（含 objects[].region）/ steps / edges 生成或修改独立原型工程目录中的主可操作原型；目录为步骤 0 解析的 `prototype_project_root`（默认建议 `prototype/`），它由 git 跟踪、随 Mission 分支隔离，不在 `project-knowledge/` 下、不在 mission artifact 下。
- **先有骨架再上像素、从组件库装配**：原型挂在应用外壳（`data-shell`）里、按区域树组织（`data-region`）、区域里渲染**业务组件实例**（`data-bizcomp`，复用 `business-components.md` 或本次新定义的）、业务组件由基础组件搭、全用 `prototype/tokens.css` 的登记 token；改 / 扩既有 surface 在既有原型上原地迭代、继承既有外壳 / 区域 / 组件与设计语言，不另起一套观感。**先产出低保真 ASCII 线框、再上高保真像素（compose-before-HTML 字面成立）**：动 HTML 之前，先把区域树渲染成低保真 ASCII 线框（每个关键 surface 一张，用 ASCII 框线画区域块 + 中文占位标签，按区域树嵌套与扫描序排），存入 `visual-interaction/variants/**` 纯文本文件（如 `lowfi-wireframes.md`）。它出具极快、人扫一眼即可核对组成、AI 直接读文本、物理上无法精修——ASCII 在前定组成、HTML 在后上像素，比例 / 密度 / 视觉权重留给高保真，"低保真滑向高保真 lite"的精修化风险被介质切断；结构正确性仍由区域树 + R8 组成门兜底，ASCII 只是给人看的派生视图。线框连同「设计意图」一节，在 step-5a 与高保真原型**一起呈现给用户**——让用户既看成品、也看清组成与方向意图，便于一次性核对方向是否对。低保真 ASCII 线框是与原型并列的呈现材料，**不构成高保真之前的强制确认闸**（不另设阻断 Gate），但 designer 不得跳过其产出。
- 主可操作原型必须作为唯一默认人类入口，覆盖 P0 点击路径、关键状态和桌面端 / 移动端主要视口；页面内不得出现阅读顺序、验收场景 / 追溯、路径 / 状态展板、审查员指引、资产清单说明或组件目录。
- 阶段 artifact 下不得再新建一套 `visual-interaction/prototype/**` 主原型副本。需要保留候选画面、截图、状态覆盖或录屏时写入 `visual-interaction/variants/**` 或 `visual-interaction/evidence/**`，并在 manifest 中引用。
- 不默认生成画廊、组件、路径、状态等可见说明页面；需要补证据时写入 `visual-interaction/evidence/**`，不作为人类入口。
- 所有用户可见文字默认使用中文；允许保留的英文仅限品牌名、产品专名、代码标识、行业通用英文缩写或上游明确指定的外语文案。
- 生成可视化资产时，调用 `harness evidence visual manifest --mission <mission-id> --json` 生成 `visual-interaction-manifest.json`。
- 行为图与原型就绪后，先调用 `harness interaction project --mission <mission-id> --prototype-root <prototype_project_root> --json` 从 `behavior-graph.yaml` 生成 `views/by-suc|by-surface|by-object.md` 与驾驶舱数据 `walkthrough.js`。
- 再调用 `harness interaction prototype-check --mission <mission-id> --prototype-root <prototype_project_root> --json` 做一次对账（graph 自洽 + 布局骨架自洽 + 原型忠实完整实现），返回 `{status, findings[]}`，findings 按 category（graph/reachability/anchor/coverage/locator/upstream/composition/design_system）分。graph/reachability/anchor/coverage/composition 类 FAIL 必须在本阶段修复（design_system 默认 warn 滚动，采用组件库后升 fail），不得带病进 Gate。Stage Gate 的 `gate run` 会再次对账。
- manifest 与 trace 对账完成后，**当场**调用 `harness lint project --mission <mission-id> --json` 产出 project-lint 控制面报告（覆盖原型 trace 规约与项目其它产物级约束）。`gate_effect=block` 是原型阶段的越界 / 不合规缺口，必须立即在本阶段修复后重跑，不得带病进 Stage Gate，也不得口头改写为通过。`require_for_prototype=true` 时，`harness gate run` 会强制要求一份覆盖当前 manifest 的 fresh project-lint 报告，缺失或陈旧都会 FAIL。
- 在 `interaction.md`「原型合同与阅读顺序」段引用手写真相源；在「可视化交互资产」段引用资产清单、独立原型工程主入口（`prototype_project_root` 内）与关键变体路径，并标明主原型是唯一默认人类入口。

</step>

<step id="step-3" n="3" goal="contract.yaml 初始化 + execution_result 写入">

- 若 `contracts/interaction.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage interaction --template interaction --json`。
- 调用 `harness contract add-execution-result --artifact harness-runtime/harness/stages/<mission-id>/contracts/interaction.contract.yaml --result <interaction-designer-execution-result.yaml> --json`。
- 调用 `harness contract patch`，把交互分析方法、编号约定、交互规格、界面边界基线、界面边界变更清单、独立原型工程入口、原型界面、领域模型覆盖、路径、状态、场景、校验规则、一致性报告和义务从 `interaction.md` 与手写真相源抽取写入 `contract.yaml`，并写入可视化资产引用。
- 把 behavior-graph 摘要写入 `contract.yaml`（最小字段：`graph_path` / `page_state_ids[]` / `step_ids[]` / `flow_ids[]` / `status`）供 `contract check` 与 Gate 引用；不复制全图（SSOT 是 `behavior-graph.yaml`，已废弃 `surface_bindings`）。
- `traces_to` 必须命中 `prd.contract.yaml` 中来自验收条件、系统责任、质量与运行约束、差量规格需求或场景的追溯锚点。

</step>

<step id="step-3a" n="3a" goal="产品定义回流检查">

- 对照 `product/product-definition.md`、`product/product-domain-model.md`、`prd.contract.yaml`，检查原型设计是否引入新的系统行为、用户目标、验收场景 / 条件、领域实体、实体状态、用户动作、权限规则或范围变化。
- 对照 `product/use-case-model.md` 和 `product/acceptance-scenarios.md`，检查交互设计是否只是在实现已确认系统用例流和系统行为描述；若发现需要新增系统行为、系统用例、修改用例流或补造验收场景 / 条件，必须回流产品定义阶段。
- 如果只是把既有产品定义内容表达为界面和状态，继续审查员循环。
- 如果原型设计需要改变产品定义阶段内容，停止交互推进，将差异写入 `interaction.md`「产品定义回流检查」和契约的开放问题 / 关注点，并发起决策门或路由回产品定义阶段。
- 不得直接修改产品定义包或差量规格。

</step>

<step id="step-4" n="4" goal="审查员循环">

无轮次放行（轮次只记录修复历史，永不放行）；本轮 `interaction-reviewer` 在等同严格度下返回 PASS 时退出。

<dispatch role="interaction-reviewer" mode="spawn" />

审查简报必须包含：

- `interaction.md`、`interaction-spec/surface-model.md`、`interaction-spec/behavior-graph.yaml`、`interaction-spec/views/*`（生成）、`harness interaction prototype-check` 结果、`contracts/interaction.contract.yaml`。
- 行为图的编号约定与 flow≠state 区分。
- 包含 `visual-interaction-manifest.json`、长期原型工程主入口、低保真 ASCII 线框、关键 HTML / SVG 变体或内部证据。
- 产物标准是否被遵守：手写真相源只有 `surface-model.md` + `behavior-graph.yaml`，`views/` 必须是 `harness interaction project` 生成（带 GENERATED 头）；主原型必须落在独立原型工程目录，阶段 artifact 只保存证据。
- 若 `interaction-spec/` 出现手写的 views 或其它手写规格文件，审查简报必须要求改正。
- 长期原型工程主入口是否是主可操作原型入口，且未混入评审说明、验收场景 / 追溯、路径 / 状态展板和组件目录。
- 产品定义包、领域模型、差量规格、用户旅程 / 前端界面义务、上游约束摘要。
- 用例模型和验收场景摘要，重点说明系统行为描述、系统用例、主成功流、备选流、异常流和界面承载要求如何被 `interaction-spec` 承载。
- 原型可见文案语言检查：用户可见文字默认中文，例外项必须有来源和理由。
- **设计意图 + 表达对照**：`interaction.md` 的「设计意图」节（视觉方向 / 主角强调 / 真实内容样例 / 参考 / 非目标）、`visual-interaction/variants/**` 低保真 ASCII 线框，供审查员做表达对照（意图齐全性 + 原型是否明显违背意图）；缺意图节按 `design_intent_missing`、明显违背按 `expression_mismatch` HOLD。
- 审查员必须检查本次改动是否在独立原型工程目录上迭代；若发现每个 mission 在 artifact 下另起主原型副本，返回 HOLD。

每轮审查返回后由控制面记录审查结论；不再用 `patch --add-round` 手工维护轮次：

```bash
harness contract record-review --artifact harness-runtime/harness/stages/{mission-id}/contracts/interaction.contract.yaml --role interaction-reviewer --verdict {PASS|PASS_WITH_RISK|HOLD|BLOCKED} --subagent-id {subagent-id} --model {resolved-model} --review-basis harness-runtime/harness/artifacts/{mission-id}/interaction/interaction.md --summary {review-summary} --json
```

处理审查结论：

- HOLD / BLOCKED：先用 `harness contract record-review` 记录 verdict 与 `--blocking-gap`，再修复 `interaction.md` / 手写真相源；如原型或可视化资产存在缺口，按需修复长期原型工程、变体、预览和资产清单，记录本轮发现与修复，重新进入审查员循环。
- PASS：用 `harness contract record-review` 记录 PASS，退出循环。
- 无轮次放行：轮次只记录修复历史，永不构成放行理由，每轮以等同严格度重审，循环到 reviewer 在等同严格度下 PASS 为止。卡死时（同一阻断在修复后仍以相同根因连续 HOLD 且无实质进展，按缺口本质判断、不是"轮次到点"）不得降级通过，询问用户选择解决方向（候选**不含"接受降级批准"**：继续修 / 改范围 / 升级 BLOCKED），残留风险只能由用户在充分披露后于 Decision Gate 显式拥有并记 approval。

</step>

<step id="step-5" n="5" goal="产物门禁自检">

- 调用 `harness contract check --artifact contracts/interaction.contract.yaml --upstream prd.contract.yaml --upstream mission-contract.contract.yaml --json`。
- 调用 `harness interaction spec-check --mission <mission-id> --json`，验证手写真相源包含必备内容，且界面动作 / 字段 / 状态 / 权限可追溯到领域模型。
- 确保已先跑 `harness interaction project`（生成 views + walkthrough.js）；再调用 `harness interaction prototype-check --mission <mission-id> --prototype-root <prototype_project_root> --json`——**唯一 lint**，一次对账返回 `{status, findings[]}`（含 graph/reachability/anchor/coverage/locator/upstream/composition/design_system 类）。graph/reachability/anchor/coverage/composition 类 FAIL 必须修复（design_system 默认 warn）。
- 检查文案语言 / 中文文案一致性；未解释的外语用户可见文案是阻断项。
- 调用 `harness alignment check --mission <mission-id> --stage interaction --json`，验证界面边界 / 路径 / 状态对齐产品定义和领域模型。
- 调用 `harness interaction gate run --mission <mission-id> --json`，聚合 spec-check、prototype-check、alignment-check、feedback-sync 和审查员结论；若结果要求用户确认，进入步骤 5a。

</step>

<step id="step-5a" n="5a" goal="用户原型确认检查点">

- **默认以 harness 框架方式启动确认**：用户确认的默认入口是**演示导览播放器 `harness-prototype-frame.html`**（读 `walkthrough.js`，iframe 内嵌真实可操作原型并逐拍驱动 + 旁白讲触发 / 看到的态 / 验收点）——而不是直接把用户丢到裸 `index.html` 自己乱点。播放器系统性带用户逐 flow 走查、对照验收点，正是"确认表达是否符合意图"该用的方式。裸可操作原型作为播放器的 iframe 驱动对象保留，并额外提供**自由操作二级入口**（用户想自己点时进 `index.html`），让确认既覆盖脚本演示、也覆盖真实操作。
- **一并呈现方向材料**：连同播放器，把「设计意图」一节（`interaction.md`）与低保真 ASCII 线框（`visual-interaction/variants/**`）一起给用户，便于用户在看到成品的同时核对视觉方向 / 主角强调 / 内容样例 / 参考是否对路——方向不对在这里就纠，不要等到下游。
- 让用户确认原型是否符合产品意图、关键路径、状态和文案预期。若需起本地预览服务，遵守 `.harness/docs/prototype-standard.md` 的「本地预览服务端口（多项目共存，强制）」：先探测端口，被占用就换空闲端口，绝不 kill / stop 其它项目已在跑的服务，并把实际 URL / 端口告诉用户（默认给出播放器 URL）。
- 主流程把确认结果写入 `harness-runtime/harness/traces/{mission_id}/user-prototype-confirmation.md`，包含：
  - 主原型入口路径或 URL
  - 用户确认的路径 / 状态范围
  - 用户反馈原文或摘要
  - PASS / FAIL 结论
  - 是否允许进入下一阶段
- 若用户确认 FAIL：按反馈回步骤 1 / 步骤 2 修复手写真相源和同一独立原型工程目录，重新进入审查员循环；不得另建一个新的 artifact 原型副本。
- 若用户确认 PASS：调用 `harness approval append --mission <mission-id> --type checkpoint --stage interaction --status approved --json`，然后重新调用 `harness interaction gate run --mission <mission-id> --json`，确认用户原型确认已纳入门禁。

</step>

<step id="step-6" n="6" goal="阶段完成 + 工作图输出">

- 调用 `harness mission stage complete interaction --mission <mission-id> --json`。`design-interaction-check-gate-pass` 钩子会阻断缺少门禁 PASS 报告的完成动作。
- 当前阶段动作产物 `interaction.md` + 手写真相源、`visual-interaction/` manifest / evidence 和用户确认记录，必须写入统一 artifact store / trace，并在契约 YAML 的 `work_graph_artifact.artifact_refs[]` 段引用；长期原型工程作为 living prototype project 被引用，不复制进 Work Graph。
- `interaction.md` 必须保留「沉淀候选」段：列出可复用原型模式、系统界面边界信息架构、**布局骨架 / 区域树**、**本次新定义的业务组件（绑 OBJ/SUC）/ 基础组件**、领域对象到界面的映射、交互约束、可复用的设计 token，以及是否应进入项目知识（`design-system/` 各分层 / 累积图 `regions`）或能力规格。
- 任务阶段的手写真相源是本次原型工程增量变更合同，不是长期按任务堆积的系统原型库；主可操作原型必须保留在独立原型工程目录中持续迭代，不得把规格和审查资料混排成文档页。

</step>

</steps>

<failure_paths>

| Failure | 触发条件 | 处理 |
|---|---|---|
| `prototype-not-needed` | 步骤 0 原型必要性判断 `needed=false` | 合法跳过：已写 `prototype-necessity.json`(needed=false + reason + decided_by) 作凭证，不产 interaction 重产物，按 board-router 推进到 solution；不是 BLOCKED，是正常出栈 |
| `prd-feedback-required` | 步骤 3a 发现原型需要改变产品定义、领域模型、验收场景 / 条件或范围 | 停止交互推进，记录差异，发起决策门或路由回产品定义阶段 |
| `interaction-designer-blocked` | 步骤 1 返回 BLOCKED | 缺失输入则回步骤 0；范围冲突则询问用户；决策门则暂停等待用户 |
| `visual-manifest-missing` | 步骤 2 资产清单失败或未引用长期原型工程主入口 | 检查长期原型入口和变体；缺失则重新触发 `visual-interaction-design`，其它情况升级 BLOCKED |
| `interaction-spec-incomplete` | 步骤 5 门禁发现手写真相源缺失关键合同内容或追溯关系 | 回步骤 1 补齐智能体交接合同；不得只补 HTML 预览 |
| `review-stuck` | 步骤 4 卡死（修复后仍以相同根因连续 HOLD 无实质进展，非轮次到点） | 重新归因后进入用户检查点（候选仅：继续修 / 改范围 / 升级 BLOCKED，不含降级批准） |
| `gate-fail` | 步骤 5 `harness interaction gate run` FAIL | 按失败检查回步骤 1 或步骤 2 修复 |
| `user-prototype-confirmation-fail` | 步骤 5a 用户确认原型不符合预期 | 按反馈回步骤 1 / 步骤 2，在同一独立原型工程目录继续迭代并重新审查 |

</failure_paths>

</workflow>
# interaction / references

本目录存放 **interaction skill 产出固定交互标准包时引用的框架级 pattern、schema 与 checklist**。当前为空——按需补，不必铺满。

## 装什么

面向 `interaction.md`、`surface-model.md`、`behavior-graph.yaml` 和 `contracts/interaction.contract.yaml` 产出过程的**可复用骨架**，例如：

- **page-state 状态范式**：loading / empty / error / permission / keyboard+focus 作为 page_state 的最小列表与判定问题
- **行为图 schema**：`surface-model.md`（含 surface 目录机器段）、`behavior-graph.yaml`（page_states/steps/edges/flows）的字段定义与最小示例
- **user flow pattern**：登录、注册、支付、onboarding、多步表单、长列表/分页、权限分支、撤销/重做等通用流程的合同骨架
- **domain → UI 映射 pattern**：领域实体 / 聚合 / 状态机 / 命令到 screen / state / action 的映射范式
- **E2E obligation pattern**：每条用户路径必须落到 locator / `data-testid` 的命名约定与最小覆盖清单
- **a11y / 键盘焦点 / 权限分支 checklist**：与 `craft/` 横切规则的引用关系
- **consistency report 范式**：怎么证明本次原型与既有 surface / baseline 一致

## 不装什么

- **HTML / SVG / CSS / preview 资产**——那是 [visual-interaction-design/references/](../../visual-interaction-design/references/README.md) 与 `harness-runtime/harness/artifacts/<id>/interaction/visual-interaction/` 的工作面。
- **项目自身的具体 capability spec**——走 `project-knowledge/specs/<capability>/spec.md`，本目录只装与项目无关的 pattern。
- **本次 mission 的 delta spec**——走 `harness-runtime/harness/artifacts/<id>/product/specs/<capability>/spec.md`。
- **HTML seed / layout 物料库 / 设计 token 套件**——Harness 的终态交付不是 HTML artifact（详见下节 "与 Open Design 的区别"）。

## 与 Open Design (`nexu-io/open-design`) `design-templates/` 的区别

| | OD `design-templates/` | 本目录 |
|---|---|---|
| 终态产物 | 单文件 HTML artifact，给最终用户 | 固定交互标准包，给下游 solution / technical_analysis / execute / E2E 消费 |
| 资产形态 | `template.html` seed + `layouts.md` paste-ready section + `checklist.md` + design-system tokens | 用例实现 / 界面模型 / 交互合同 schema、flow pattern、state matrix、E2E obligation、a11y checklist（纯文本/markdown/yaml） |
| 角色 | LLM 拼装 HTML 的物料库 | interaction-designer agent 起草合同的骨架库 |
| HTML / preview 地位 | 终态交付 | 仅作设计证据，受 manifest / Gate 约束（见 visual-interaction-design） |

OD 那一套不能照搬——它的"四件套"在 Harness 里对应的是 `visual-interaction-design/` 下的设计证据规范，而不是 interaction 合同骨架。

## 三层资产关系

```
框架级 pattern（本目录）
   │   被 interaction skill workflow 引用
   ▼
项目级 spec（project-knowledge/specs/<capability>/）
   │   建立长期能力契约
   ▼
本次 mission delta（harness-runtime/harness/artifacts/<id>/product/specs/<capability>/）
   │   本次任务的差量
   ▼
本次 mission 产物（interaction.md / interaction-spec/surface-model.md / interaction-spec/behavior-graph.yaml / interaction-spec/views/ / contracts/）
```

## 维护提示

- 新增 pattern 命名 kebab-case，每个 pattern 一个 `.md`，开头一句话写"何时引用"。
- pattern 若与 `craft/` 横切规则重叠，本目录只引用、不复制。
- 若同一 pattern 被 solution / test-planning 等其他 skill 也引用，提案抽到与 `craft/` 同层的横切目录，再回到本目录引用。
