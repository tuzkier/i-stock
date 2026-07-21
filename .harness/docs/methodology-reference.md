# 方法论参考手册

> **性质**：策展式参考文档（Curated Reference）。为 HarnessV2 每个生命周期阶段映射业界成熟方法论。
> **用法**：各技能的工作流在执行前引用对应章节，获取"怎么思考"的指导。
> **原则**：引用并整合业界方法，不自造。

---

## 导航

| # | 生命周期阶段 | HarnessV2 技能 | 主要方法论 |
|---|------------|-----------------|-----------|
| 1 | [问题发现](#1-问题发现) | `discovery` | Event Storming · Impact Mapping · JTBD |
| 2 | [需求工程](#2-需求工程) | `prd` | BDD/GWT · User Story Mapping · OpenSpec · IEEE 29148 |
| 3 | [架构设计](#3-架构设计) | `design` (solution) | C4 Model · ADR · DDD · Arc42 |
| 4 | [API 设计](#4-api-设计) | `design` (tech-design) | OpenAPI 3.x · Google API Guide · REST Guidelines |
| 5 | [数据建模](#5-数据建模) | `design` (tech-design) | 数据库范式 · Event Sourcing · CQRS |
| 6 | [任务规划](#6-任务规划) | `breakdown` | Vertical Slicing · OpenSpec propose |
| 7 | [开发实践](#7-开发实践) | `execute` | TDD · BDD · ATDD · Trunk-Based Development |
| 8 | [代码评审](#8-代码评审) | `code-review` | Google 代码评审 · Conventional Comments |
| 9 | [调试](#9-调试) | `systematic-debugging` | Systematic Debugging · Delta Debugging |
| 10 | [测试策略](#10-测试策略) | `verify` | Test Pyramid · Testing Trophy · Contract Testing · PBT |
| 11 | [安全工程](#11-安全工程) | `code-review` (security) | OWASP Top 10 · STRIDE · Secure by 设计 |
| 12 | [性能工程](#12-性能工程) | `verify` (NFR) | USE Method · RED Method |
| 13 | [重构](#13-重构) | `execute` (Refactor 阶段) | Fowler Refactoring Catalog · Code Smells |
| 14 | [文档策略](#14-文档策略) | `delivery` | Diátaxis Framework · ADR |
| 15 | [部署](#15-部署) | `delivery` (扩展) | 12-Factor App · GitOps · Progressive 交付 |
| 16 | [运维与可观测性](#16-运维与可观测性) | `retrospective` (扩展) | SRE · Three Pillars · OpenTelemetry |

---

## 1. 问题发现

**HarnessV2 技能**：`discovery` → `discovery-brief.md`

### 推荐方法论

| 方法论 | 作者/来源 | 最适合场景 |
|--------|----------|-----------|
| **Event Storming** | Alberto Brandolini | 领域复杂、多角色协作的系统 |
| **Impact Mapping** | Gojko Adzic | 需要对齐业务目标与交付物 |
| **Jobs-to-be-Done (JTBD)** | Clayton Christensen | 需要挖掘用户真实动机 |

### 核心实践

**Event Storming 关键步骤**：
1. 识别领域事件（橙色便利贴，过去时描述，如"订单已创建"）
2. 找命令（蓝色，触发事件的动作）
3. 找聚合根（黄色，处理命令的对象）
4. 识别外部系统和 Policy（规则）
5. 按时间轴排列，找热点（复杂、争议点）

**Impact Mapping 结构**（树状）：
```
Goal（业务目标）
 └── Actor（谁影响目标）
 └── Impact（需要改变的行为）
 └── Deliverable（我们能做什么）
```

**JTBD 核心提问**：
- 用户在什么情境下"雇用"这个产品？
- 他们真正要完成的是什么工作？
- 当前解法有哪些摩擦点？

### HarnessV2 检查表

- [ ] `discovery-brief.md` 中问题空间定义清晰（不是解决方案）
- [ ] 核心用户旅程至少识别 2-3 个
- [ ] 不确定项显式标注，带影响说明
- [ ] 和 `mission-contract.md` 的范围对齐

---

## 2. 需求工程

**HarnessV2 技能**：`prd` → `product/product-definition.md`

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **BDD / Given-When-Then** | Dan North | 可执行的行为规格，消除歧义 |
| **User Story Mapping** | Jeff Patton | 以用户旅程组织需求，防止遗漏 |
| **规格驱动开发** | OpenSpec (Fission-AI) | 规格先行，AI 与人对齐后再写代码 |
| **IEEE 29148** | IEEE/ISO/IEC | 需求文档标准化，完整性检查表 |

### 核心实践

**BDD Given-When-Then**（HarnessV2 product/product-definition.md 已采用）：
```
Given: <前置条件，系统和用户所处的状态>
When: <用户或系统触发的动作>
Then: <可观测的结果>
```
- 每条验收条件必须可自动化测试
- 排除技术实现细节（"Given 用户 JWT token 有效" ✗ → "Given 用户已登录" ✓）

**User Story Mapping 结构**（水平 = 活动/旅程；垂直 = 优先级）：
```
用户活动（高层）
 └── 用户任务（中层步骤）
 ├── P0 用户故事（必须上线）
 ├── P1 用户故事（第一个迭代）
 └── P2 用户故事（后续迭代）
```

**OpenSpec 核心理念**（[github.com/Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)）：
- **规格先行**：propose → 审查 → apply，不在 chat 里边说边做
- **规格 Delta**：描述变化，不只是最终状态（便于审查）
- **持久化**：规格与代码共同版本化（HarnessV2 的 `harness-runtime/harness/stages/` 已实现）

**IEEE 29148 需求质量检查（6 条）**：
1. **原子性**：一条需求只表达一个能力
2. **可测试性**：能写出对应测试用例
3. **可追溯性**：追溯到 Success Criteria 和用户旅程
4. **无歧义**：只有一种解释
5. **一致性**：与其他需求不冲突
6. **优先级**：P0/P1/P2 明确标注

### HarnessV2 检查表

- [ ] 每条验收场景 / 条件有 Given/When/Then 格式
- [ ] 需求追溯到验收场景（product/product-definition.md 追溯矩阵已填写）
- [ ] 需求描述能力，不泄露实现（无技术名词）
- [ ] Out of 范围附理由
- [ ] 不确定项列入"待确认问题"，附截止日期

---

## 3. 架构设计

**HarnessV2 技能**：`design` → `solution.md` + `tech-design.md`

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **C4 Model** | Simon Brown | 4 层抽象：上下文 → Container → Component → Code |
| **Architecture Decision Records (ADR)** | Michael Nygard | 结构化记录"为什么"做此决策 |
| **Domain-Driven 设计 (DDD)** | Eric Evans | 统一语言、界限上下文、聚合根 |
| **Arc42** | Gernot Starke | 轻量级 12 节架构文档模板 |

### 核心实践

**C4 Model 4 层**（[c4model.com](https://c4model.com)）：
```
L1: System Context — 系统与外部用户/系统的关系
L2: Container — 系统内的部署单元（App/DB/Queue）
L3: Component — 每个 Container 内的主要组件
L4: Code — 类/函数级别（通常由代码生成）
```
HarnessV2 的 tech-design.md 对应 L2-L3 层级。

**ADR 格式**（[adr.github.io](https://adr.github.io)）：
```markdown
# ADR-001: <决策标题>
状态: 提议 / 已接受 / 废弃 / 被取代

## 上下文
为什么需要做这个决策？有哪些限制？

## 决策
我们决定做什么。

## 后果
这个决策带来了什么？正面和负面影响。

## 备选方案（被拒绝的）
为什么没选这些方案。
```
HarnessV2 的 `solution.md` 方案对比段落应包含 ADR 要素。

**DDD 核心概念（战略层）**：
- **Ubiquitous Language**：团队共用词汇表（写进 `discovery-brief.md`）
- **Bounded 上下文**：每个上下文内模型自治，跨上下文通过 Anti-Corruption Layer
- **上下文 Map**：上下文间的集成关系（Shared Kernel / Customer-Supplier / Conformist）

**DDD 模块边界判断**：
- 一个模块 = 一个 Bounded 上下文
- 模块间耦合 = 需要定义 API 契约
- 共享核心 = 需要 Shared Kernel（明确标注）

### HarnessV2 检查表

- [ ] solution.md 有 ≥2 个候选方案（已要求）
- [ ] 选定方案附 ADR 要素（为什么选、为什么不选其他）
- [ ] tech-design.md 模块边界清晰（DDD 界限上下文）
- [ ] 架构关键决策用 ADR 格式记录
- [ ] 非功能需求（NFR）映射到架构战术

---

## 4. API 设计

**HarnessV2 技能**：`design` → `tech-design.md`（接口变化段落）

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **OpenAPI 规格 3.x** | OpenAPI Initiative | 机器可读的 API 描述，支持代码生成和测试 |
| **Google API 设计 Guide** | Google | 资源导向设计，标准命名 |
| **Microsoft REST API Guidelines** | Microsoft | 一致性规范，错误处理，版本策略 |

### 核心实践

**Contract-First 流程**（推荐）：
1. 先写 OpenAPI YAML/JSON 定义
2. 人工审查（资源是否合理？命名是否一致？）
3. 根据规格生成 client/server stub
4. 实现服务逻辑

**资源导向设计原则**（Google API 设计 Guide，[cloud.google.com/apis/design](https://cloud.google.com/apis/design)）：
- 用名词不用动词：`/orders/{id}` ✓，`/getOrder` ✗
- 标准方法：GET(List/Get) · POST(Create) · PUT/PATCH(Update) · DELETE
- 集合用复数：`/users`，单个资源：`/users/{id}`

**向后兼容规则**：
- ✅ 可以：新增可选字段、新增资源、新增枚举值
- ❌ 不可以：删除字段/资源、改字段类型、改语义
- 破坏性变更 → 新版本（`/v2/`）

**错误响应标准化**（RFC 7807 Problem Details）：
```json
{
 "type": "https://example.com/errors/validation",
 "title": "Validation Error",
 "status": 422,
 "detail": "field 'email' is required",
 "instance": "/orders/123"
}
```

### HarnessV2 检查表

- [ ] tech-design.md 接口变化段落有 Before/After 对比
- [ ] 新接口有兼容性说明
- [ ] 涉及外部系统时提供 OpenAPI 规格引用
- [ ] 错误码有标准化说明

---

## 5. 数据建模

**HarnessV2 技能**：`design` → `tech-design.md`（数据变化段落）

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **数据库范式（1NF-BCNF）** | E.F. Codd | 消除冗余和更新异常 |
| **Event Sourcing** | Martin Fowler / Greg Young | 事件追加为唯一事实来源 |
| **CQRS** | Greg Young | 读写分离，按访问模式优化 |

### 核心实践

**范式检查**（关系型 DB 设计）：
- **1NF**：每个字段原子值，无重复组
- **2NF**：1NF + 非主键字段完全依赖于主键
- **3NF**：2NF + 无传递依赖（非主键字段间无依赖）
- 实际决策：OLTP 用 3NF；OLAP 可适度反范式

**Event Sourcing 适用条件**（[martinfowler.com/eaaDev/EventSourcing](https://martinfowler.com/eaaDev/EventSourcing.html)）：
- 需要完整审计轨迹
- 需要时间点查询（Point-in-Time Query）
- 需要事件重放
- 注意：引入额外复杂度，仅在以上需求存在时使用

**CQRS 判断**（[martinfowler.com/bliki/CQRS](https://martinfowler.com/bliki/CQRS.html)）：
- 读写比例悬殊（读多写少或写多读少）
- 读模型需要跨多个聚合
- 性能要求差异大
- 注意：最终一致性问题，团队需要接受

**数据变更分类**：
```
新增字段 → 向后兼容，迁移简单
修改字段类型 → 需要迁移脚本，可能不兼容
删除字段 → 先弃用（deprecate），再删除（两个版本周期）
新增表/集合 → 无风险
删除表/集合 → 高风险，需要完整数据迁移计划
```

### HarnessV2 检查表

- [ ] tech-design.md 数据变化段落有具体变更内容（不是"修改数据库"）
- [ ] 每条数据变更有迁移策略和回滚方案
- [ ] 使用 Event Sourcing/CQRS 有充分理由
- [ ] 高风险数据变更（删除/重命名）触发 Decision Gate

---

## 6. 任务规划

**HarnessV2 技能**：`breakdown` → `execution-brief.md`

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **Vertical Slicing** | Agile community | 按用户价值纵切，每个 slice 可独立验证 |
| **OpenSpec propose 工作流** | Fission-AI | 规格 → 设计 → 任务清单，结构化变更提案 |

### 核心实践

**Vertical Slice 原则**：
- 一个 slice = 从 UI 到数据库的完整薄片
- 每个 slice 独立可部署、可验证
- ❌ 水平切（先做所有 UI，再做所有 API）
- ✅ 垂直切（先做完整的"用户登录"，再做"用户注册"）

**任务项粒度判断**：
- 一个 TDD 循环可完成（一般 < 4 小时）
- 有明确的 Done 定义
- 有对应的测试文件
- 依赖关系明确（可以在 execution-brief.md 的实现顺序表中体现）

**OpenSpec 任务清单格式**（参考 [github.com/Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)）：
- 每个任务项映射到具体的规格变更
- 任务项描述包含：做什么、怎么验证

### HarnessV2 检查表

- [ ] 每个任务项对应一个 TDD 循环（不过大）
- [ ] 任务项有测试/实现/重构三步骤
- [ ] 实现顺序按依赖关系排列
- [ ] Definition of Done 明确

---

## 7. 开发实践

**HarnessV2 技能**：`execute` → 代码 + 测试

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **TDD** | Kent Beck | Red → Green → Refactor，测试驱动设计 |
| **BDD** | Dan North | Given/When/Then 规格驱动实现 |
| **ATDD** | Agile community | 验收测试先行，确保实现满足需求 |
| **Trunk-Based Development** | Google / Thoughtworks | 频繁小提交主干，短生命周期分支 |

### 核心实践

**TDD 循环**（HarnessV2 已强制）：
```
1. Red: 写一个失败的测试（描述期望行为）
2. Green: 写最少的代码让测试通过（不求完美）
3. Refactor: 在绿灯下重构（测试保护）
4. 重复
```
- 禁止跳过 Red 阶段（不能先写实现再补测试）
- Green 阶段只求通过，Refactor 阶段再求质量

**ATDD 流程**（推荐在执行开始前）：
1. 从 execution-brief.md 的验收场景转换为自动化测试（`test.skip()`）
2. 所有验收场景测试先写好，全部 skip
3. 逐个任务项让对应测试变绿

**Trunk-Based Development 核心纪律**（[trunkbaseddevelopment.com](https://trunkbaseddevelopment.com)）：
- 分支存活 < 2 天
- 每次提交都可 CI 通过
- 功能开关（Feature Flag）保护未完成功能
- 每天至少一次推送到主干

### HarnessV2 检查表

- [ ] 每个任务项先写失败测试再实现
- [ ] 不写没有测试覆盖的代码
- [ ] Refactor 阶段在绿灯下进行
- [ ] 禁用词检查：不出现"应该可以"/"看起来对"

---

## 8. 代码评审

**HarnessV2 技能**：`code-review` → `code-review.md`

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **Google 代码评审 Practices** | Google Engineering | 重设计轻风格，4 小时周转目标 |
| **Conventional Comments** | Paul Slaughter | 结构化评审意见，意图清晰 |

### 核心实践

**Google 代码评审核心原则**（[google.github.io/eng-practices/review](https://google.github.io/eng-practices/review/)）：
- 审查重点优先级：**设计 > 功能 > 复杂度 > 测试 > 命名 > 注释 > 风格**
- 4 小时响应目标（不阻塞开发流）
- 对事不对人（评审代码，不评价开发者）
- LGTM 可以带保留意见（"LGTM but please fix X before 合并"）

**Conventional Comments 格式**（[conventionalcomments.org](https://conventionalcomments.org)）：
```
<label> [decorators]: <subject>
[discussion]

标签：suggestion / issue / nitpick / praise / question / thought / chore
装饰：(blocking) / (non-blocking) / (if-minor)
```
例：`issue (blocking): 这里有竞态条件，并发写入会导致数据丢失`

**HarnessV2 多角色审查分工**：
- `architecture-reviewer`：架构合规（对齐 tech-design）
- `security-reviewer`：安全问题（OWASP Top 10）
- `correctness-reviewer`：逻辑正确性、测试覆盖

### HarnessV2 检查表

- [ ] 三个审查员（架构/安全/正确性）均已独立审查
- [ ] 阻断性问题必须修复后才能继续
- [ ] 每条发现有定位（文件:行号）

---

## 9. 调试

**HarnessV2 技能**：`systematic-debugging` → 根因分析；缺陷闭环由 `bug-fix` 主导，按需调用 `systematic-debugging` 作为 carrier

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **Systematic Debugging** | Andreas Zeller《Why Programs Fail》 | 科学方法用于调试，不猜 |
| **Delta Debugging** | Andreas Zeller | 自动化最小化失败输入 |

### 核心实践

**科学调试流程**（Zeller 方法）：
```
1. 观察：失败的具体表现是什么（可重现的）
2. 假设：哪里可能出问题（有依据，不瞎猜）
3. 实验：最小改动验证假设
4. 观察：结果是否和假设一致
5. 结论：找到根因 → 由当前 carrier 修复 → 验证修复不破坏其他
```

**二分定位法**：
- 二分代码：用 `git bisect` 找引入缺陷的 commit
- 二分输入：找最小的触发失败的输入
- 二分配置：找触发失败的最小配置差异

**3 次法则**（HarnessV2 已有）：
- 同一假设失败 3 次 → 放弃这个假设，换方向
- 防止在错误方向上无限投入

**调试前置检查**（避免"随机改代码"）：
- 错误信息完整读完了吗？
- 能稳定复现吗？
- 最近改了什么？（git diff / git log）
- 在最小化的场景里能复现吗？

### HarnessV2 检查表

- [ ] 先能稳定复现再开始调试
- [ ] 假设有依据（不是"感觉是这里"）
- [ ] 每次实验只改一个变量
- [ ] 根因确认后，写回归测试防复发

---

## 10. 测试策略

**HarnessV2 技能**：`verify` → `verification-report.md`

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **Test Pyramid** | Mike Cohn | 底多顶少：单元 > 集成 > E2E |
| **Testing Trophy** | Kent C. Dodds | 重心在集成测试（现代应用更适合） |
| **Contract Testing** | Pact Foundation | 消费者驱动，微服务间独立验证 |
| **Property-Based Testing** | QuickCheck / Hypothesis | 自动生成随机输入，验证性质 |

### 核心实践

**Test Pyramid vs Testing Trophy 选择**：
- 纯函数/算法/工具库 → **Test Pyramid**（单元测试为主）
- 现代 Web/API 应用 → **Testing Trophy**（集成测试为主）
- 微服务架构 → **Contract Testing** 必加

**Test Pyramid 比例参考**（[martinfowler.com/articles/practical-test-pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)）：
- 70% 单元测试（快，隔离，覆盖边界）
- 20% 集成测试（覆盖模块协作）
- 10% E2E 测试（覆盖关键用户旅程）

**Contract Testing 适用场景**（[docs.pact.io](https://docs.pact.io)）：
- 微服务之间有 API 依赖
- 需要独立部署每个服务
- 流程：Consumer 写 pact → Provider 验证 pact

**Property-Based Testing 适用场景**：
- 纯函数（输入 → 输出）
- 数据转换/序列化
- 数学性质（交换律、幂等性等）

**验证证据标准**（HarnessV2 铁律）：
- ✅ 命令执行输出（`npm test` 的实际结果）
- ⚠️ 断言计数（仅作补充）
- ❌ "应该可以"/"测试覆盖率足够"

### HarnessV2 检查表

- [ ] 测试分层策略根据项目类型选择
- [ ] 每条验收场景有对应的可自动化测试
- [ ] 新代码有足够的测试覆盖（不以覆盖率数字为唯一标准）
- [ ] `verification-report.md` 有实际命令输出

---

## 11. 安全工程

**HarnessV2 技能**：`code-review`（`security-reviewer` Agent）

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **OWASP Top 10** | OWASP Foundation | Web 应用最常见安全漏洞清单 |
| **STRIDE Threat Modeling** | Microsoft | 6 维度威胁建模 |
| **Secure by 设计** | NIST SSDF | 安全从设计开始，不是后补 |

### 核心实践

**STRIDE 威胁建模**（在 solution.md 设计阶段执行）：

| 字母 | 威胁类型 | 例子 |
|------|---------|------|
| **S** | Spoofing 欺骗 | 伪造用户身份 |
| **T** | Tampering 篡改 | 修改传输数据 |
| **R** | Repudiation 抵赖 | 否认执行过某操作 |
| **I** | Info Disclosure 信息泄露 | 暴露敏感数据 |
| **D** | Denial of Service 拒绝服务 | 耗尽资源 |
| **E** | Elevation of Privilege 提权 | 获取未授权权限 |

**OWASP Top 10 必查项**（[owasp.org/Top10](https://owasp.org/Top10/)）：
1. 注入（SQL/命令/LDAP）
2. 失效的身份认证
3. 敏感数据暴露
4. XML 外部实体（XXE）
5. 访问控制失效
6. 安全配置错误
7. XSS
8. 不安全的反序列化
9. 已知漏洞的组件
10. 日志记录不足

**4 个必查项**（所有项目）：
- **认证**：密码哈希（bcrypt/argon2）、会话管理
- **授权**：最小权限、服务端验证
- **加密**：传输加密（TLS）、敏感数据加密
- **输入验证**：所有外部输入做白名单验证

### HarnessV2 检查表

- [ ] 设计阶段 solution.md 有 STRIDE 分析（涉及安全场景时）
- [ ] code-review 的 security-reviewer已审查 OWASP Top 10
- [ ] 无硬编码密钥/密码
- [ ] 所有外部输入有验证

---

## 12. 性能工程

**HarnessV2 技能**：`verify`（NFR 验证）

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **USE Method** | Brendan Gregg | 资源视角：Utilization · Saturation · Errors |
| **RED Method** | Tom Wilkie | 服务视角：Rate · Errors · Duration |

### 核心实践

**USE Method**（[brendangregg.com/usemethod](https://brendangregg.com/usemethod.html)）
- 对每个物理/虚拟资源（CPU、内存、磁盘、网络）检查：
 - **U**tilization：资源使用率（0-100%）
 - **S**aturation：排队程度（请求等待）
 - **E**rrors：错误计数
- 适合：找系统瓶颈、容量规划

**RED Method**（[grafana.com/files/grafanacon_eu_2018/Tom_Wilkie_GrafanaCon_EU_2018.pdf](https://grafana.com/files/grafanacon_eu_2018/Tom_Wilkie_GrafanaCon_EU_2018.pdf)）
- 对每个服务/微服务检查：
 - **R**ate：每秒请求数（吞吐量）
 - **E**rrors：每秒错误数（错误率）
 - **D**uration：请求延迟（p50/p95/p99）
- 适合：监控服务健康、发现降级

**性能测试工作流**：
```
1. 基线测量（变更前记录 USE + RED 数据）
2. 变更实施
3. 对比测量（变更后记录同一组数据）
4. 判断：变化是否在可接受范围内
```
没有基线就没有优化，只有随机变化。

**NFR 中性能指标必须可量化**（HarnessV2 product/product-definition.md 已要求）：
```
❌ "响应速度快"
✅ "API 响应时间 p95 < 200ms（正常负载，APM 监控验证）"
```

### HarnessV2 检查表

- [ ] product/product-definition.md NFR 中的性能指标可量化、有测量方式
- [ ] 变更前有基线数据
- [ ] 性能敏感变更在验证阶段执行对比测量

---

## 13. 重构

**HarnessV2 技能**：`execute`（TDD Refactor 阶段）

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **Refactoring Catalog** | Martin Fowler | 70+ 命名重构手法，每个有明确机制 |
| **Code Smells** | Fowler / Beck | 设计问题的表面指标，触发重构 |

### 核心实践

**常见 Code Smells**（[refactoring.com/catalog](https://refactoring.com/catalog/)）：

| 代码异味 | 描述 | 通常的重构 |
|---------|------|-----------|
| Long Method | 方法过长（>20 行） | Extract Method |
| Large Class | 类过大（职责过多） | Extract Class |
| Long Parameter List | 参数列表过长（>4 个） | Introduce Parameter Object |
| Duplicate Code | 相同逻辑在多处 | Extract Method / Pull Up Method |
| Feature Envy | 方法更关心其他类的数据 | Move Method |
| Data Clumps | 总是同时出现的数据 | Extract Class |
| Switch Statements | 大量 switch/if-else | Replace Conditional with Polymorphism |

**重构原则**：
- 重构必须有测试保护（TDD 的绿灯阶段）
- 每次只做一个重构（不混合重构和功能变更）
- 小步快跑（每步重构都能通过测试）
- 按 Fowler 命名法识别和记录重构（便于审查）

**重构 vs 修缺陷的区分**：
- 重构：代码结构变化，外部行为不变，测试不改
- 修缺陷：外部行为修正，必须先有失败测试

### HarnessV2 检查表

- [ ] Refactor 阶段在所有测试绿灯下进行
- [ ] 每次重构小而完整
- [ ] 重构后所有测试仍通过

---

## 14. 文档策略

**HarnessV2 技能**：`delivery` → `delivery-package.md`

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **Diátaxis Framework** | Daniele Procida | 4 类文档，按读者需求分类 |
| **Architecture Decision Records (ADR)** | Michael Nygard | 持久化"为什么"，不只是"是什么" |

### 核心实践

**Diátaxis 4 类文档**（[diataxis.fr](https://diataxis.fr)）：

| 类型 | 读者目标 | 内容形式 | 例子 |
|------|---------|---------|------|
| **Tutorial** | 学习 | 引导式步骤 | "入门指南" |
| **How-to Guide** | 完成目标 | 步骤清单 | "如何配置 SSL" |
| **Reference** | 查找信息 | 结构化列表 | "API 文档" |
| **Explanation** | 理解原理 | 叙述性讨论 | "为什么选择这个架构" |

HarnessV2 的阶段文档分类：
- `product/product-definition.md` → Explanation（理解问题）
- `tech-design.md` → Reference + Explanation（查接口 + 理解设计）
- `execution-brief.md` → How-to Guide（如何完成这批任务）
- `delivery-package.md` → Reference（查变更清单）

**交付包最低文档要求**：
- ✅ 做了什么（变更清单）
- ✅ 为什么这样做（ADR 链接或摘要）
- ✅ 如何运行/验证
- ✅ 遗留问题
- ✅ 下一步建议

### HarnessV2 检查表

- [ ] `delivery-package.md` 包含以上 5 项
- [ ] 重要架构决策有 ADR 引用
- [ ] 交接文档按 Diátaxis 明确区分类型

---

## 15. 部署

**HarnessV2 技能**：`delivery`（当前侧重打包，部署指导不足）

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **12-Factor App** | Heroku / Adam Wiggins | SaaS 应用的 12 条最佳实践 |
| **GitOps** | Weaveworks | Git 为基础设施唯一事实来源 |
| **Progressive 交付** | industry | 渐进式发布，降低变更风险 |

### 核心实践

**12-Factor App 关键因素**（[12factor.net](https://12factor.net)）：

| 因素 | 核心要求 | 常见违规 |
|------|---------|---------|
| Codebase | 一个代码库，多个部署 | 多仓库共享代码 |
| Dependencies | 显式声明所有依赖 | 依赖系统全局工具 |
| Config | 配置存储在环境变量 | 配置硬编码在代码 |
| Backing Services | 附加资源即插即用 | 区分本地和远程数据库 |
| Processes | 无状态、无共享 | 本地文件作持久存储 |
| Logs | 写到 stdout | 写到文件 |

**Progressive 交付策略**（[progressive-delivery.com](https://progressive-delivery.com)）：
```
Feature Flag → Canary (5%) → Canary (25%) → 全量
每步观察：错误率 ↑？延迟 ↑？业务指标 ↓？
```
- 出现异常 → 立即回滚（<1 分钟）
- 全量后 → 清理 Feature Flag

**部署前检查表**：
- [ ] 配置是否外置（无硬编码环境配置）
- [ ] 数据库迁移脚本是否幂等
- [ ] 回滚计划是否存在并测试过
- [ ] 健康检查端点是否可用
- [ ] 告警规则是否配置

### HarnessV2 检查表

- [ ] `delivery-package.md` 包含部署步骤
- [ ] 高风险变更有渐进发布计划
- [ ] 数据变更有迁移 + 回滚脚本

---

## 16. 运维与可观测性

**HarnessV2 技能**：`retrospective`（扩展）

### 推荐方法论

| 方法论 | 作者/来源 | 核心价值 |
|--------|----------|---------|
| **Site Reliability Engineering (SRE)** | Google | 错误预算、SLO/SLI、无责复盘 |
| **Three Pillars of Observability** | industry | Metrics + Logs + traces |
| **OpenTelemetry** | CNCF | 厂商中立的遥测标准 |

### 核心实践

**SRE 核心概念**（[sre.google](https://sre.google)）：
- **SLI**（Service Level Indicator）：实际测量值（如请求成功率）
- **SLO**（Service Level Objective）：目标值（如 99.9% 可用性）
- **Error Budget**：SLO 允许的失败空间（1 - SLO）
- **原则**：错误预算耗尽 → 停止发布新功能，专注可靠性

**Three Pillars**：
- **Metrics**：聚合数值（RED + USE），用于趋势和告警
- **Logs**：离散事件，用于调试（结构化日志 > 非结构化）
- **traces**：请求链路，用于分布式系统诊断

**OpenTelemetry 关键点**（[opentelemetry.io](https://opentelemetry.io)）：
- 一次插桩，输出到任意后端（Jaeger/Tempo/Zipkin/Langfuse）
- SDK 支持：Python/Go/Java/Node.js 等主流语言
- LLM 可观测性：Langfuse 和 Arize Phoenix 均支持 OTel

**无责事后复盘（Blameless Postmortem）结构**：
```
1. 时间线：按时序还原事件经过
2. 根因分析：5 Why 找到根本原因
3. 贡献因素：哪些系统/流程因素导致问题
4. 行动项：防止复发的具体措施（负责人 + 截止日期）
5. 不做：不追责个人
```

### HarnessV2 检查表

- [ ] `delivery-package.md` 包含运维注意事项
- [ ] 关键业务路径有 SLO 定义
- [ ] 有结构化日志方案
- [ ] 变更上线后有观测计划
