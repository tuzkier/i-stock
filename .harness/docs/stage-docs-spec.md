# 阶段文档规范

## 这是什么

本文件定义了 HarnessV2 模板中所有阶段文档的写作标准、结构约定和质量要求。

## 为什么阶段文档很重要

阶段文档在 HarnessV2 中承担双重角色：

1. **给人审阅**：产品负责人、技术负责人、验收者需要快速理解当前进展和关键决策
2. **给下游消费**：下一个阶段的 AI 需要从中提取上下文，才能准确执行

如果文档写得像内部状态 dump，人无法审阅；如果文档写得像散文，AI 无法提取。好的阶段文档两者兼顾。

## 统一写作原则

### 首先是正式文档

每份阶段文档都是一份可以独立拿给人看的正式文档。不是工作草稿，不是内部状态转储，不是审查员检查清单。

### 中文为主

阶段文档默认以中文表达。英文只作为专用词、机器标识、字段名、命令、路径、状态码、真实专名、行业通用缩写或引用上游原文时的辅助说明；必要时写成“中文（English）”。除这些例外外，标题、结论、需求、验收、风险、决策和面向用户的说明一律以中文为准。

### 先结论后展开

每个一级章节先写 1-3 句结论性判断，再用列表、表格或场景展开细节。读者应能只读标题和首段就抓到主线。

### 高信息密度

每句话都必须承载信息。消除以下反模式：

- "系统将允许用户..." → "用户可以..."
- "值得注意的是..." → 直接陈述事实
- "为了..." → "因为..."
- 对话式填充和重复 → 直接、精练的表述

### 正文与附录分离

- **正文**：问题、边界、决策、验收——读者做决定所需的全部信息
- **附录**：检查清单、claims to 验证、文件路径、执行提示——实现层细节

### 可验证的标准

所有验收条件、需求、约束都必须是可验证的，不是"用户友好""高性能"这类模糊描述。

## 八份阶段文档的定位

### `mission-contract.md`

**一句话**：本轮任务的授权契约。

**写给谁看**：AI 自己（在整个执行过程中反复查阅）+ 人类确认者

**核心回答**：做什么、不做什么、什么算完成、AI 能自己决定到什么程度

**质量标准**：objective 必须一句话讲清楚；scope_out 每条必须附理由；acceptance_scenarios 必须可验证

### product/product-definition.md

**一句话**：定义问题空间和需求边界。

**写给谁看**：产品负责人 + 方案设计者 + 实现负责人

**核心回答**：为什么要做、做什么、不做什么、什么算完成

**质量标准**：人类读者应能在 5 分钟内抓到主线；需求必须可追溯到用户场景；验收项必须描述可观测行为

**吸收 BMAD 的什么**：BMAD 的 PRD 强调 information density、traceability chain、SMART criteria、dual-audience optimization。HarnessV2 的 product/product-definition.md 应达到同等标准。

### product/product-domain-model.md

**一句话**：按 DDD 定义产品领域语义、边界、行为和规则。

**写给谁看**：产品负责人 + 交互设计者 + 方案设计者 + 技术设计者 + 测试负责人

**核心回答**：这个需求属于哪个业务域、限界上下文在哪里、统一语言是什么、核心聚合和聚合根是什么、哪些命令/事件/不变量/状态/权限/异常必须被后续阶段保留。

**质量标准**：必须覆盖 Strategic DDD、Tactical DDD、Rules & Constraints、Traceability、Downstream Guidance；不适用项必须说明原因；不得写数据库、接口路径、缓存、队列、框架或部署方案；关键需求必须能追溯到 command / invariant / state / permission / event。

### solution.md

**一句话**：记录方案选择和关键取舍。

**写给谁看**：技术负责人 + 产品负责人

**核心回答**：考虑了哪些方案、选了哪个、为什么、放弃了什么

**质量标准**：至少列出 2 个候选方案；每个方案有明确的利弊分析；选择理由不能是"更好"，必须是具体的判断依据

### interaction.md

**一句话**：定义关键交互流程和用户体验边界。按需产出。

**写给谁看**：前端实现者 + UX 审阅者

**核心回答**：用户在每个界面为了完成目标会看到什么、能做什么、系统如何响应、失败后如何继续；领域对象、trace、locator 和可视化资产如何作为交接证据支撑这个判断

**质量标准**：PRD 后默认需要产出，除非任务明确为 API-only / 无界面 / 纯后端 / CLI-only。interaction.md 必须根据产品定义、差量 spec 和 DDD 领域模型说明关键 surface 的 User Goal、Entry / Exit、ASCII Wireframe、Screen Priority、Actions、Interaction Rules、States、Recovery 和 PRD 回流检查；`interaction-spec/` 是所有 UI delivery mode 共用的 Surface Interaction Spec，必须由 PRD / Domain Model / 验收场景派生并持续追溯它们，不能替代 PRD，也不能脱离 PRD 自行新增产品语义。trace、domain mapping、locator、E2E obligation 是交接证据，不能替代交互决策。涉及复杂 UI / user journey 时，必须引用按真实系统 surface 组织的 `interaction-spec/` 作为 AI handoff 合同。interactive_prototype 路线还必须引用 `visual-interaction/visual-interaction-manifest.json`、HTML / SVG 变体、preview 或等价截图 / 录屏作为人类评审证据；frontend_engineering 路线必须引用 `frontend-changeset.md`、前端工程 patch、MSW scenario 和用户浏览器走查证据作为实现证据。修改既有 UI 时必须写明 baseline 和 surface changeset，不能按任务堆孤立页面。HTML / 图片 / 前端代码不能替代 `interaction-spec/`；用户确认后的原型或前端变更必须先同步更新 `interaction-spec/`，涉及验收场景、用户旅程、领域模型、权限或范围变化时必须回流 PRD / Decision Gate。

### tech-design.md

**一句话**：把方案压成模块级可执行的技术蓝图。

**写给谁看**：实现者（AI 或人）

**核心回答**：改哪些模块、接口怎么变、数据怎么变、怎么验证

**质量标准**：改动范围必须精确到模块或文件级；接口变化必须写出 before/after；验证策略必须可执行

### execution-brief.md

**一句话**：给执行阶段的压缩上下文包。

**写给谁看**：执行阶段的 AI

**核心回答**：要做什么、硬性约束是什么、已知风险是什么、从哪里开始

**吸收 BMAD 的什么**：BMAD 的 create-story 工作流会把 PRD、architecture、UX、previous learnings 压缩成一份 story 文件，让 dev Agent "拥有 flawless 实现所需的一切"。execution-brief.md 的目标一样：把上游所有关键信息压缩成一份执行者可以直接消费的文档。

**质量标准**：执行者读完这一份文档就能理解任务边界、验收、TDD 边界和证据要求，不需要再回去翻 prd 和 solution。execution-brief 首次写盘时必须已经包含 Parent task + parent-local `atomic_task_queue` 的完整结构；不得先产 Parent task 骨架，再用 `writing-plans` 作为 breakdown 后的常规补丁。Parent task 是 Work Graph TASK 边界，只保留父任务顺序、完成边界、DoD、规格引用、Parent 级 TDD 边界和 evidence 权威；execute 必须按每个 Parent task 内的 `atomic_task_queue.execution_units[]` 执行。

#### Execution Units / parent-local atomic_task_queue

**一句话**：`execution-brief.md` 内部由 Atomic Tasks（原子任务）组成的执行队列。

**写给谁看**：SDD 执行子 Agent、需要精确落地步骤的人类工程师

**核心回答**：execution-brief 的每个 Parent task 如何继续拆成 Atomic Tasks；每个 Atomic Task 改哪些文件、参考哪些同项目样板间或相似实现习惯、遵守什么接口/数据契约、TDD 的 Red/Green/Refactor 范围和禁止范围是什么、如何准备测试数据、运行什么命令、预期失败/通过信号是什么、交付哪些证据

**质量标准**：Execution Units 必须覆盖全部任务项、验收场景 / Scenario、DoD、Test Obligation 和 evidence_required；每个 Parent task 必须内嵌 `atomic_task_queue.status=ready`，且至少包含一个 Atomic Task。每个 Atomic Task 只包含一个明确工程行动或验证行动，具备输入、输出、涉及文件、代码模式参考、接口/数据契约、TDD scope、测试前置、验证命令、证据要求和停止条件；TDD scope 必须写清 Behavior under test、Red scope、Green scope、Refactor scope、Out of scope、Required assertions、测试数据边界、test doubles 边界和 fault / mutation signal；代码模式参考只用于骨架、项目实现习惯和风格对齐，不用于复用业务逻辑；不得包含完整可提交实现或完整测试文件；Execution Units 必须经过 `execution-plan-effectiveness-reviewer` 审查，通过前 execute 不得开始。Atomic Task 必须内嵌在对应 Parent task 下；若映射缺失或与父任务边界冲突，execute 必须 BLOCKED，回到 breakdown / Stage Gate 修复，而不是跳过队列或直接执行父任务。

### `verification-report.md`

**一句话**：记录验证证据和结论。

**写给谁看**：验收者 + 交付者

**核心回答**：验证了什么、怎么验证的、结果是什么、有没有遗留问题

**质量标准**：每个验收标准都必须有对应的验证结果；验证方法必须可复现

### `delivery-package.md`

**一句话**：任务交付的最终总结。

**写给谁看**：用户 + 未来接手者

**核心回答**：做了什么、结果是否满足验收、哪些没做、下一步建议是什么

**质量标准**：用户读完就知道这轮做了什么、做到什么程度；遗留项必须明确列出

## 文档之间的依赖关系

```
mission-contract
 ↓
prd
 ↓
interaction
 ↓
solution
 ↓
tech-design
 ↓
execution-brief
 ↓
[代码实现]
 ↓
verification-report
 ↓
delivery-package
```

上游文档是下游文档的输入约束。AI 在写下游文档时，应该主动引用上游文档的关键结论，而不是重新发明。

## 文件位置

所有阶段文档实例写入 `harness-runtime/harness/stages/<mission-id>/`。

模板位于 `harness-runtime/templates/`。
