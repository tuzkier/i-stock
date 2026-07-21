# 依赖影响工作流

> **触发条件、反幻觉协议、分类标准见 `SKILL.md`，不在此重复。**

**审查约定：** `dependency-impact.md` 写入后、用户确认前，须经过 `dependency-validity-reviewer` 审查-修复循环。旧通用文档 reviewer 不作为 dependency-impact 默认审查组。

**可调用的子 Agent：**
- `integration-impact-expert` — 依赖影响执行专家
- `dependency-validity-reviewer` — 依赖有效性审查员

**执行约定：** 由本阶段主流程通过 `spawn_agent` 直接调用上述子 Agent。主流程必须先读取 `.harness/common/agents/<role>.md`，并把文件完整原文作为子 Agent prompt 第一段，再附加路径化 Task Envelope（角色目标、输入路径、输出路径、完成条件、write_scope / read_scope、同 barrier 角色关系和停止条件）。Task Envelope 只传路径和边界，不复述 role package 的角色边界，不粘贴上游文档全文，除非角色包或本 workflow 明确要求内联。等待返回时不得把固定短等待当作失败；返回后由主流程汇总裁决，并把结构化执行/审查结果登记到当前 Mission Slice 的 dependency evidence；不得把子 Agent 调用替换为主 Agent 自审，也不得把结构化 YAML 追加到 `dependency-impact.md`。若 dependency-impact 被 `work_graph.lanes` 注册为独立 action，结构化结果由调用方写入该 action 配置指定的外部 contract / evidence artifact。

---

## 核心顺序原则

**由外到内，先环境后代码。**

```
第一层：基础设施 → 数据库表/Queue/Job/Cache/配置密钥，有没有、够不够
第二层：外部业务系统 → 依赖的其他系统，是否存在、接口是否就绪、能不能接入
第三层：自身代码 → 确认前两层具备之后，才看自身代码需要改什么
```

> 如果第一层缺失，讨论第三层没有意义。
> 如果第二层接口未就绪，实现第三层只是在等待依赖。

---

## 初始化

1. 读取当前 Mission Slice；dependency-impact 是当前 slice 的依赖证据 carrier，不是默认 Work Graph lane action，除非 `work_graph.lanes` 显式注册了对应 action。
2. 读取 `harness-runtime/harness/missions/<mission-id>/mission-contract.md`，提取范围内的变更清单。
3. 调用 `harness-cli` 执行 `harness context check --json`；PASS 则读取 `project-context.md` 了解系统整体结构；FAIL 时按 `project-context` 规则处理，并在 dependency-impact evidence 中记录 `inputs_missing.project_context=true`，不得静默继续。
4. 调用 `harness-cli` 执行 `harness config snapshot --json`，确认 `brownfield`、依赖影响策略摘要和 `work_graph.lanes`；不得直接读取 `harness-runtime/config/harness.yaml`。
5. **（spec.enabled=true 时）** 读取 `project-knowledge/specs/` 下与本次任务相关能力的spec.md，提取当前系统已承诺的 Requirement 清单。在第三层（自身代码）分析时，优先核查哪些 Requirement 会因本次变更被影响。
6. 确认 `query-api-docs` 技能是否可用（存在 `.harness/common/skills/query-api-docs/`）。
7. 确认 `cognee-knowledge` 技能是否可用（读取 `.harness/common/skills/cognee-knowledge/SKILL.md`）；Cognee 以 **官方 MCP**（如 `list_data`）为主，**不要**为技能去改 `mcp.json`。
8. 若已配置 Cognee MCP：用 MCP **`list_data`**（或备选脚本 `cognee-search.sh datasets`）列出数据集，记录哪些外部系统有知识库支撑。
9. 确认 `gitnexus-impact-analysis` 技能是否可用（存在 `.harness/common/skills/gitnexus/gitnexus-impact-analysis/`）；若可用，读取 `gitnexus://repo/{name}/context` 检查索引是否最新（若 "Index is stale" → 提示用户运行 `npx gitnexus analyze`）。
10. 读取 dependency-impact role policy；默认执行子 Agent 为 `integration-impact-expert`，审查子 Agent 为 `dependency-validity-reviewer`；后续实际调度必须用 `spawn_agent` 调用。

---

## 执行

<workflow skill="dependency-impact" version="2">

<step n="1" goal="绑定当前 Mission Slice">
 - 确认当前 Mission Slice 存在，并记录 `primary_nodes`、`related_nodes`、`control_plane.stage`、`lane_action.output_artifact`。
 - 若本技能由 discovery / design / prd 等阶段内部触发，`dependency-impact.md` 作为当前 Mission Slice 的 evidence artifact 写入，不创建独立 dependency-impact stage key。
 - 若项目配置将 dependency-impact 注册为独立 `work_graph.lanes` stage，则必须按该 Mission Slice 的 `control_plane.stage` 执行；缺失注册表时不得自行推导独立阶段。
 - Hard gate：没有 Mission Slice 或无法确定调用方 slice 时，dependency-impact BLOCKED；不得回退到固定阶段链。
</step>

<step n="2" goal="专业角色调度">
 - 用 `spawn_agent` 调用 `integration-impact-expert` 子 Agent；提供 Mission Contract、project-context、API 文档、配置、Cognee/GitNexus evidence；dependency claims 必须带 source evidence。
 - 分析完成后，用 `spawn_agent` 调用 `dependency-validity-reviewer` 子 Agent；提供 dependency-impact artifact、source evidence 和 confidence labels；无来源依赖声明必须 HOLD。结构化 verdict 写入调用方 Mission Slice 的 dependency evidence 或独立 action 的外部 contract / evidence artifact，`dependency-impact.md` 只保留面向人的审查摘要。
</step>

<step n="3" goal="提取需求中的依赖线索">
 - 从任务契约的目标和范围内 中，逐句识别所有提到或暗示的外部事物：

 列出所有出现的：
 - 业务系统名称（"通知中心"、"用户服务"、"报表系统"、"ERP"...）
 - 基础设施词汇（"异步"→Queue、"定时"→Job、"缓存"→Cache、"存储"→DB/OSS）
 - 动作暗示（"发送"→邮件/短信/推送服务、"记录"→DB、"同步"→外部系统）
 - 明确提到的第三方服务或 API

 **输出：初步依赖候选清单**（此时不判断是否存在，只列出）

 - 条件：某个词语暗示了依赖但不明确
 - 向用户提问澄清，而不是自行假设
 - 例如："需求中提到'异步处理'，请确认：是否需要消息队列？用的是哪个？"
</step>

<step n="4" goal="第一层：基础设施配置信息确认">
 - 对候选清单中所有基础设施类依赖，检查的不是"软件有没有装"，而是"这个功能所需的具体配置信息是否已经确定"：

 **不同类型基础设施，需要确认的配置信息不同**：

 | 类型 | 需要确认的配置信息 |
 |------|-----------------|
 | 数据库 | 用哪张表？表结构定义好了吗？有 migration 吗？需要新增字段还是新建表？索引？ |
 | 消息队列 | Exchange/Topic 名称？Queue 名称？消息的 schema/格式？生产者是谁？消费者是谁？失败策略？ |
 | 定时任务 | Job 名称？cron 表达式？入参？超时时间？失败重试策略？由哪个服务托管？ |
 | 缓存 | 用哪个 namespace/DB？key 的命名规则？TTL？缓存失效策略？ |
 | 对象存储 | 用哪个 Bucket？目录结构？文件命名规则？访问权限？ |
 | 配置中心 | 需要哪些配置项？配置项的 key 叫什么？已经在配置中心定义了吗？ |

 **检查方式（按顺序查找，找到就记录，找不到就标 UNCERTAIN/MISSING）**：
 1. 读取 `docs/` / `README.md` / 设计文档 — 看有没有对应的配置规范说明
 2. 读取 `.env.example` / `config/` / 配置文件 — 看有没有对应的配置项定义
 3. 读取 `db/migrations/` / `schema/` — 看数据库结构定义是否已存在
 4. 读取 `project-context.md` — 看有没有基础设施约定记录

 ```markdown
 ## 基础设施配置层确认

 | 基础设施 | 需求来源 | 需要确认的配置信息 | 状态 | 证据/缺口 |
 |---------|---------|-----------------|------|---------|
 | DB: order_notifications 表 | "记录通知状态" | 表结构、字段定义 | missing | db/migrations/ 中无此表 |
 | Queue: 通知消息 | "异步发送通知" | Exchange名、Queue名、消息schema | uncertain | .env.example 有 MQ_HOST，但无具体 Queue 定义 |
 | Job: 每日对账 | "每日定时对账" | cron表达式、入参、托管服务 | uncertain | README 提到 xxl-job，但无此 Job 的配置记录 |
 | Cache: 用户信息缓存 | "缓存用户信息" | key命名规则、TTL | missing | config/ 中无缓存 key 规范 |
 ```

 - 条件：某基础设施的配置信息不明确或未定义
 - 标记为 UNCERTAIN 或 MISSING
 - 生成具体问题向用户澄清，例如："通知消息队列用的 Queue 名称是什么？消息格式有定义吗？"
 - 不要自行假设 Queue 名或表结构，假设了后面会产生不一致
</step>

<step n="5" goal="第二层：外部业务系统确认">
 - 对候选清单中所有业务系统类依赖，逐一确认：该系统存不存在、提供了什么、我们需要的接口是否就绪

 **对每个外部业务系统，回答四个问题**：

 1. **系统存在吗？**
 - 检查 `project-context.md` 中是否有记录
 - 检查 `.harness/common/skills/query-api-docs/` 是否有对应 API 文档（若有，使用该技能查询）
 - 检查 `docs/` 目录是否有集成文档

 2. **我具体需要它的什么？**
 - 是调用它的某个接口？还是读取它的数据库？还是订阅它的事件？
 - 明确具体的接口名称 / 数据字段 / 事件名称

 3. **这个具体接口/数据/事件已经就绪了吗？**
 - 接口文档有吗？
 - 接口已上线了吗？还是对方也在开发中？
 - 鉴权方式确认了吗？（API Key / OAuth / 内网直连）

 4. **测试/开发环境能接通吗？**
 - 有没有沙盒环境或 mock？

 **证据获取优先级（按顺序执行，前一步有结果可减少后续查询）**：

 1. **项目内文档**：`project-context.md`、`docs/`、配置文件
 2. **YAPI 实时查询**：`query-api-docs` 技能（如果系统在 YAPI 有项目）
 3. **Cognee 知识图谱查询**：`cognee-knowledge` 技能 — **Cognee 官方 MCP** 的 `search`（及按需 `list_data`）；无 MCP 时用 `cognee-search.sh`
 4. **GitNexus 对方仓库分析**：若对方系统的仓库已在 GitNexus 建立索引，用 `gitnexus-exploring` + `gitnexus-impact-analysis` 直接分析其代码（见下方）
 5. **标记 UNCERTAIN 并向用户求证**：仅当以上全部无结果时

 > **反幻觉强化**：在标记任何外部依赖为 `[ASSUMED]` 或 `uncertain` 之前，
 > **必须先按 `cognee-knowledge` 技能查 Cognee**（优先 **官方 MCP `search`**，读取 `.harness/common/skills/cognee-knowledge/SKILL.md`）。
 > 查询无果且对方仓库已在 GitNexus 中索引时，再用 GitNexus 分析。两者均无果才允许标记。

 **多仓库场景：用 GitNexus 分析外部系统代码**

 当本次任务需要**另一个团队的仓库提供接口或修改逻辑**时（不是你自己的代码），若该仓库已在 GitNexus 索引：

 ```
 // 4a. 探索对方仓库，理解其结构和能力
 READ gitnexus://repo/{对方仓库名}/context → 代码库全貌
 gitnexus_query({query: "<你需要的功能>"}) → 找到相关模块和执行流

 // 4b. 确认对方是否已有你需要的接口/逻辑
 gitnexus_context({name: "<对方的接口/函数名>"}) → 查看该接口的调用关系和实现位置

 // 4c. 若需要对方新增或修改逻辑，评估对他们的影响
 gitnexus_impact({
 target: "<对方需要改动的函数>",
 direction: "upstream",
 minConfidence: 0.8
 })
 → 评估对方改动的 blast radius，判断可行性和风险，作为协作沟通依据
 ```

 **两种典型场景**：

 | 场景 | 用什么 | 目的 |
 |------|--------|------|
 | 对方已有接口但我不确定是否符合需求 | `gitnexus-exploring` | 直接查看接口签名、参数、返回值 |
 | 需要对方新增/修改逻辑 | `gitnexus-impact-analysis` | 评估他们的改动风险，给协作沟通提供依据 |

 ```markdown
 ## 外部业务系统层确认

 | 系统 | 我需要什么 | 系统存在? | 接口就绪? | 证据/文档 | 缺口 |
 |------|-----------|---------|---------|---------|------|
 | 通知中心 | POST /notify 发推送 | confirmed | uncertain | project-context.md 有提及，但无接口文档；GitNexus 索引中找到 NotificationService，但无 /notify 端点 | 需对方新增接口，blast radius 评估：影响 d=1 两处 |
 | 用户服务 | GET /users/{id} 获取邮箱 | confirmed | confirmed | docs/user-service-api.md + yapi: #1234 | 无 |
 | 财务系统 | 对账数据同步 | uncertain | missing | 无任何文档，GitNexus 未索引 | 需确认系统归属团队 |
 ```

 > **证据来源标注**：Cognee 查询标注 `cognee: <查询内容>`；YAPI 标注 `yapi: <接口ID>`；GitNexus 标注 `gitnexus: <仓库名>/<查询>`；项目文档标注文件路径。

 - 条件：项目文档和 YAPI 均无结果
 - 执行 `cognee-knowledge` 技能：用 Cognee 官方 MCP **`search`**（必要时先 **`list_data`**）；无 MCP 时用 `cognee-search.sh`
 - 若对方仓库已在 GitNexus 索引：用 `gitnexus-exploring` 探索其代码结构，确认接口是否存在
 - Cognee / GitNexus 有结果 → 整理为证据，更新状态（附对应来源标注）
 - 两者均无结果 → 此时才允许标记为 UNCERTAIN/MISSING

 - 条件：需要对方系统新增或修改逻辑
 - 若对方仓库已在 GitNexus 索引：执行 `gitnexus-impact-analysis`，评估对方改动的 blast radius
 - 将影响评估结果记录到 `dependency-impact.md` 的缺口列，作为与对方团队协作沟通的依据
 - 标记为 Blocker 或 External Dependency，明确记录：需要哪个团队提供什么、改动风险评级、预计就绪时间
</step>

<step n="6" goal="第三层：自身代码确认（仅在前两层无阻塞性缺口时执行）">
 - 条件：第一层或第二层存在未解决的 MISSING Blocker
 - 跳过此步骤，在输出中注明：因基础设施/外部系统存在阻塞，代码层分析暂缓
 - 先让用户解决 Blocker，再回来执行此步

 - 在确认环境具备之后，按以下顺序分析自身代码的变更范围和下游影响：

 **4.1 代码库全貌（使用 gitnexus-exploring）**：

 若 `gitnexus-exploring` 可用，先用 GitNexus 了解代码结构，避免在陌生代码库中凭猜测定位变更范围：
 ```
 READ gitnexus://repo/{name}/context → 代码库概览（模块数、staleness 状态）
 READ gitnexus://repo/{name}/clusters → 各功能区域及内聚性
 gitnexus_query({query: "<变更涉及的功能>"}) → 找到相关执行流和模块
 ```
 若索引过旧（"Index is stale"）→ 提示用户运行 `npx gitnexus analyze` 后继续。

 **4.2 变更范围定位**（必须实际扫描，禁止猜测）：
 - 结合 GitNexus clusters/query 结果 + `project-context.md`，识别需要新增/修改的文件
 - 找到实际文件路径，确认现有代码中是否已有可复用逻辑

 **4.3 下游影响扫描（优先使用 gitnexus-impact-analysis）**：

 对每个将要修改的关键函数/接口/数据模型，使用 GitNexus 进行 blast radius 分析：
 ```
 gitnexus_impact({
 target: "<函数名或接口名>",
 direction: "upstream", // 找谁依赖我
 minConfidence: 0.8,
 maxDepth: 3
 })
 ```

 按深度解读结果：

 | 深度 | 风险级别 | 含义 | 处理方式 |
 |------|---------|------|---------|
 | d=1 | **WILL BREAK** | 直接调用方，必然受影响 | 必须逐一评估兼容性 |
 | d=2 | LIKELY AFFECTED | 间接依赖，很可能受影响 | 重点关注，需测试覆盖 |
 | d=3 | MAY NEED TESTING | 传递性影响 | 记录，酌情测试 |

 若已有 staged changes，额外运行：
 ```
 gitnexus_detect_changes({scope: "staged"}) → 映射当前改动到受影响的执行流
 ```

 若 GitNexus 不可用，回退到手动代码搜索：
 - 搜索调用将要修改函数的所有地方（记录文件路径）
 - 搜索依赖将要修改数据模型的所有地方

 **识别破坏性变更**：修改别人在用的接口签名、删字段、改枚举值等。

 ```markdown
 ## 自身代码层

 ### 变更范围
 | 模块/文件 | 变更类型 | 定位来源 |
 |---------|---------|---------|
 | src/services/order.ts | 新增状态变更逻辑 | gitnexus_query("order status") → OrderService |
 | src/jobs/reconcile.ts | 新增，需要创建 | 无现有文件 |

 ### 下游影响（GitNexus blast radius）
 | 被影响对象 | 深度 | 风险 | 影响方式 | 兼容性 |
 |-----------|------|------|---------|-------|
 | OrderController | d=1 | WILL BREAK | CALLS OrderService.updateStatus | 新增方法，无破坏 |
 | authRouter | d=2 | LIKELY AFFECTED | 通过 OrderController 间接依赖 | 需回归测试 |
 | 前端订单详情页 | d=1 | WILL BREAK | 依赖 GET /orders API 字段 | 字段新增，向后兼容 |

 > 证据来源：gitnexus_impact({target: "OrderService.updateStatus", direction: "upstream"})
 ```
</step>

<step n="7" goal="汇总与行动项">
 - 将三层分析结果汇总为清晰的行动清单：

 ```markdown
 ## Blockers（必须解决才能开始写代码）

 ### 基础设施缺口
 - [ ] **RabbitMQ**：docker-compose 中无定义。行动：确认是新增还是复用现有MQ，责任人：[待定]
 - [ ] **对象存储**：无任何配置。行动：确认 provider（阿里云OSS / S3），责任人：[待定]

 ### 外部系统缺口
 - [ ] **通知中心接口文档**：系统存在但无文档。行动：向通知中心团队索取，截止：[日期]
 - [ ] **财务系统**：系统归属不明。行动：确认负责团队，责止：[日期]

 ## 已确认就绪（可以开始的部分）

 - [x] 用户服务 GET /users/{id} 接口文档完整，可直接接入
 - [x] MySQL orders 表已存在，字段确认满足需求
 - [x] 自身代码变更范围清晰，无破坏性变更

 ## 证据缺口（需要人工补充信息的项）

 | 缺口 | 验证方式 | 责任人 | 截止时间 |
 |------|---------|-------|---------|
 | Cron Job 调度系统类型 | 问运维或看生产环境配置 | [待定] | PRD 前 |
 | 通知中心是否支持批量发送 | 看接口文档或咨询对方团队 | [待定] | 设计前 |
 ```

 - 写入 `harness-runtime/harness/stages/<mission-id>/dependency-impact.md`
 - 在当前 Mission Slice 的执行证据中登记 `dependency-impact.md` 路径；若当前 slice 已有阶段状态，只更新该 `control_plane.stage` 的 evidence / obligations，不创建独立 dependency-impact stage key。
</step>

<step n="8" goal="依赖有效性审查（审查-修复循环）">
 - 读取 `mission-contract.md`，提取范围与约束摘要

 <!-- ⚠️ 以下循环是连续执行的。修复后必须立即重新审查，不得暂停、不得等待用户输入、不得结束当前回合。
 唯一合法退出条件：dependency-validity-reviewer 返回 PASS / 无阻断，或达到最大轮次。 -->
 - 循环：max_rounds=3；退出条件：本轮 dependency-validity-reviewer 返回 PASS / 无阻断

 - Round start：
 - 用 `spawn_agent` 调用 `dependency-validity-reviewer` 子 Agent，brief：dependency-impact 路径 + source evidence 清单 + confidence labels + Mission Contract 范围与约束摘要 + project-context 技术约束。
 - 要求 reviewer 在 `role_verdict` 中覆盖：dependency claim 来源证据、assumed dependency 验证动作、blast radius 置信度、Blocker 证据链、blocking_gaps。

 - 分支：审查结论
 - 情况：HOLD / BLOCKED / 有阻断性发现
 - 修复 `dependency-impact.md`（补充证据、修正矛盾或标注待验证项），记录本轮发现与修复
 - 立即回到 round_start，重新用 `spawn_agent` 调用 `dependency-validity-reviewer` 对修复后的全文进行全量审查
 - Hard gate：修复完成 ≠ 审查通过。只有 `dependency-validity-reviewer` 重新审查后确认无阻断，才能退出循环。禁止修复后直接跳过重审。
 - 情况：PASS / 无阻断性发现
 - 审查通过，退出循环


 - 条件：达到最大轮次后仍有阻断性发现
 - 发起 Decision Gate，向用户展示遗留阻断问题清单
 - 等待用户回复
 - 条件：用户提供了解决方向或授权调整
 - 按用户指导修改 `dependency-impact.md`
 - 重置轮次计数，重新回到 round_start 继续审查循环
 - 条件：用户选择接受遗留问题（降级通过）
 - 调用 `harness-cli` 执行 `harness approval append --mission <mission-id> --type tradeoff --stage dependency-impact --status approved --comment "<用户原话>" --json`；不得只在文档末尾 prose 记录。
 - 当前 Mission Slice dependency evidence 或独立 action 的外部 contract 必须保留完整未解决 findings 并标注 `accepted_by_user=true`。

 - 将面向人的审查摘要附加到 `dependency-impact.md` 末尾；结构化 `role_verdicts` 必须登记到当前 Mission Slice dependency evidence 或独立 action 的外部 contract / evidence artifact。
 - 将 `dependency-impact.md` 标记为当前 Mission Slice 的已完成 evidence artifact；是否推进 Work Graph 只由调用方阶段的 Stage Gate 和 lane action 决定。
</step>

<step n="9" goal="与用户确认">
 - 向用户展示三层的确认结果：

 - **第一层（基础设施）**：X 项已具备，Y 项缺失需解决
 - **第二层（外部系统）**：X 个系统就绪，Y 个有缺口，Z 个需要对方配合
 - **第三层（自身代码）**：[就绪 / 暂缓，等待前两层解决]
 - **总结**：现在可以开始的范围是什么，必须先解决的是什么

 - 询问用户：
 - 这些缺口中，哪些你已经知道答案了？
 - 哪些是确认要新建的（不是已有但没文档）？
 - 有没有我没识别到的依赖系统？

 - 条件：用户提供了新信息，文档内容发生变化
 - 更新 `dependency-impact.md` 中对应条目的状态，重新整理 Blockers 列表
 - 重新执行 Step 8 审查循环（文档变了，必须让 Agent 重新确认）

 - 条件：用户无新信息，确认内容正确
 - 确认通过，返回调用方当前 Mission Slice；后续由调用方阶段的 Stage Gate / Board Router 决定是否推进 Work Graph。
</step>

</workflow>

---

## 反合理化

| 诱惑 | 真相 |
|------|------|
| "Queue 肯定有，先写代码" | Queue 名叫什么？消息格式定义了吗？不知道就是没有。写了也对不上 |
| "数据库肯定有这张表" | 表结构定义在哪？字段够用吗？没有 migration 就是没有 |
| "对方系统肯定能提供这个接口" | 肯定≠确认。对方可能也在开发，或者接口字段对不上 |
| "这个小功能不依赖什么外部系统" | 需求里写了"发通知"、"同步数据"，这就是外部依赖 |
| "先把代码写好，环境问题后面补" | 环境是 Blocker，代码写完了也上不了线 |
| "我改的这个函数应该没有其他地方调用" | 用 gitnexus_impact 查一下再说，d=1 的直接调用方往往超出预期 |
| "这个字段改动影响不大" | gitnexus_detect_changes 跑一遍，看看有多少执行流经过这里 |
