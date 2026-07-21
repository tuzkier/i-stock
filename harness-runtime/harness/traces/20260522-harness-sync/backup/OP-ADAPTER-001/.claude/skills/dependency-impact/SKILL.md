---
name: dependency-impact
description: '当棕地项目变更涉及现有模块/服务/API、外部依赖、共享服务、数据模型、跨团队接口，或用户询问影响范围/依赖关系时必须使用。当依赖是否存在只能靠猜测时立即使用，禁止靠想象输出依赖列表。触发词：依赖评估、影响分析、blast radius、依赖不确定、会不会影响到X。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# 依赖影响 — 依赖与影响评估

## 核心原则

**反幻觉协议（Anti-Hallucination 协议）**

> 每条依赖必须有证据来源（文件路径、API 文档、配置文件、Cognee 查询结果）。
> 没有证据 → **先查 Cognee 知识图谱** → 仍无结果才标注 `[ASSUMED]` + 必须有验证行动项。
> "这个功能可能依赖 X" 是缺陷，不是分析结论。
> 禁止使用：可能、大概、应该、一般来说、通常。
> **证据获取顺序**：项目文档 → YAPI（query-api-docs）→ Cognee 官方 MCP（cognee-knowledge 技能：`search` / `list_data` 等）→ 标记 ASSUMED。

---

## 何时使用

**HARD-GATE（以下任一条件满足，探索必须先执行此技能）：**

- `brownfield: true` 且变更涉及现有模块/服务/API
- 任务接入评估 `外部依赖: medium 或 high`
- 变更涉及数据模型（新增字段、表结构调整、枚举变更）
- 变更涉及多个团队/系统共用的接口
- 用户描述中出现"会不会影响 X"、"X 依赖这个吗"、"这个改了其他地方会不会炸"

**可跳过：**

- `brownfield: false`（纯绿地，无现有系统）
- 变更范围仅限叶节点组件（无其他系统调用它，它也不调用外部状态）
- 用户明确说"这是一个完全独立的新模块"

---

## 分析顺序：由外到内，先环境后代码

**第一层：基础设施配置信息**（最先确认）
- 检查的不是"软件有没有装"，而是"这个功能所需的配置信息是否已经明确"
- 数据库：用哪张表？表结构定义好了吗？有 migration 吗？
- Queue：Queue/Topic 名称确定了吗？消息 schema 定义了吗？生产者消费者各是谁？
- Job：Job 名、cron 表达式、入参、失败策略确定了吗？
- 缓存：key 命名规则、TTL、失效策略定义了吗？
- 配置中心：需要的配置项 key 已经定义了吗？

**第二层：外部业务系统**（基础设施确认后）
- 依赖的系统存在吗？
- 我需要它的哪个具体接口/数据？
- 这个接口现在就绪了吗？有文档吗？鉴权方式确认了吗？
- 测试环境能接通吗？

**第三层：自身代码**（前两层无阻塞时才执行）
- 自身代码哪些地方需要改？
- 改了之后谁会受到影响（下游调用方、数据消费方）？— 优先用 **GitNexus** 做图索引分析（`gitnexus-impact-analysis`），得到 d=1/d=2/d=3 精确影响链
- 是否有破坏性变更？

> 第一层有缺口 → 不进入第三层。环境是 Blocker，代码写完也上不了线。

---

## 依赖状态分类

| 状态 | 含义 | 要求 |
|------|------|------|
| `confirmed` | 已在代码/文档中找到，可直接使用 | 必须附文件路径或文档链接 |
| `uncertain` | 预期存在但未验证 | 必须列出验证方法 + 责任人 |
| `missing` | 需要但完全不存在 | 必须列入范围或 Blocker |
| `deprecated` | 存在但已废弃，不应依赖 | 必须找替代方案 |

---

## 工具分工

| 工具 | 服务层 | 作用 |
|------|--------|------|
| `query-api-docs`（YAPI） | 第二层 | 查外部系统实时接口文档 |
| `cognee-knowledge` | 第二层 | 查知识图谱里已入库的外部系统/接口信息 |
| `gitnexus-exploring` | 第二层 + 第三层 | **多仓库均适用**：探索任意已索引仓库的模块结构和执行流。第二层用于理解外部系统代码，判断对方是否有能力提供接口/改动逻辑；第三层用于了解自身代码库全貌 |
| `gitnexus-impact-analysis` | 第二层 + 第三层 | **多仓库均适用**：分析任意已索引仓库中变更的 blast radius（d=1 直接炸 / d=2 很可能影响 / d=3 传递影响）。第二层用于评估让对方改动某处逻辑的风险；第三层用于分析自身代码的影响面 |

> **多仓库场景**：当本次任务需要**另一个团队的仓库**提供接口或修改逻辑时，若该仓库已在 GitNexus 中建立索引，则在第二层（外部系统确认）就可以用 GitNexus 分析对方代码——理解他们的结构、评估他们改动的可行性和风险，而不必等到第三层。

**证据优先级**：
- 第二层（外部系统）：`query-api-docs`（YAPI）> `cognee-knowledge`（知识图谱）> `gitnexus-exploring/impact-analysis`（对方仓库索引）> 标记 ASSUMED
- 第三层（自身代码）：`gitnexus-impact-analysis`（图索引） > 手动代码搜索 > 标记 ASSUMED

---

## 输出产物

产出 `harness-runtime/harness/stages/<mission-id>/dependency-impact.md`，内容见workflow.md。该文件默认是当前 Mission Slice 的 evidence artifact，不是独立调度 stage；只有当目标项目在 `work_graph.lanes` 显式注册 dependency-impact action 时，才按该 lane action 作为独立 Work Graph action 执行。

---

## 在工作流中的位置

默认位置：由当前 Mission Slice 的调用方阶段按需触发，常见是在 discovery 明确设计路线或关键假设之后，把 `dependency-impact.md` 作为同一 slice 的依赖证据写入。

- **触发时机**：调用方阶段已经明确设计路线或关键设计假设之后。此时才知道具体依赖什么，才能有针对性地检查。
- **为什么不在设计之后补查**：设计之后发现依赖 Blocker 会造成返工；依赖证据应作为 PRD / design 的上游约束。
- **为什么不在探索最开始强跑**：那时还没有明确设计路线或关键假设，不知道具体该检查什么配置信息。
- PRD / design 读取 `dependency-impact.md` 作为约束边界输入，不允许假设未经确认的依赖。
- Work Graph 推进由当前 Mission Slice 的 Stage Gate 和 lane action 决定；本技能不得自行宣称进入后续推进。

按 `workflow.md` 执行详细步骤。
