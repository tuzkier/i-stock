# Stage Element Model

Stage Element Model 是 Harness 各阶段共享的要素语言。它不替代 workflow、contract 或 agent prompt，也不是固定输出模板；它定义每个阶段必须识别、维护、传递给下游的核心概念。

每个阶段使用同一组列来描述自己的关键要素：

| Column | Meaning |
|---|---|
| Element | 本阶段必须识别或维护的专业要素 |
| Definition | 要素的业务 / 技术含义 |
| Source | 该要素通常来自哪里 |
| Used By | 下游谁消费这个要素 |
| Failure If Missing | 缺失时会导致什么判断或执行失败 |

## Stage Elements

### Intake

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Actual Task Goal | 用户真正希望系统、产品、代码或流程完成后的外部结果 | 用户自然语言、source material | Mission Contract、Discovery、PRD | 把阅读动作、流程要求或 Agent 指令误写成任务目标 |
| Success Definition | 完成后可观察的成功状态和验收口径 | 用户确认、Mission framing | PRD、Verify、Delivery | 下游无法判断“完成” |
| Scope Boundary | In / Out / explicit non-goals | 用户约束、Mission framing | PRD、Solution、Breakdown | 任务扩张或错误收缩 |
| Governance Level | AI 可自主推进的风险级别和 checkpoint | risk assessment | Stage Gate、autonomy loop | 该人工确认时自动推进 |

### Discovery

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Existing Capability | 当前系统、流程或知识库已有能力 | codebase、project context、knowledge、GitNexus | PRD、Solution、Tech Design | 重复设计或破坏既有行为 |
| Affected Capability | 本任务可能改变或依赖的能力 | Mission、code exploration、dependency evidence | PRD、Dependency Impact、Review | blast radius 被低估 |
| Evidence Source | 支撑发现的具体来源 | files、commands、docs、GitNexus、API docs | PRD、Stage Gate | 结论不可追溯 |
| Assumption | 尚未验证但影响后续判断的假设 | exploration gaps | PRD、Solution、Decision Gate | 假设被当成事实 |
| Risk / Constraint | 会影响方案、范围或验证的风险和约束 | codebase、external dependency、governance | Solution、Technical Analysis | 下游设计绕过风险 |

### PRD / Product Definition

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Business Object | 被业务持续追踪、有身份和生命周期的核心名词 | Mission、discovery、business reference | Interaction、Solution、Tech Design、Verify | 下游无法判断状态、规则和验收对象 |
| Business Rule | 约束对象行为、状态或权限的业务规则 | business reference、domain analysis | Scenario、AC、Tests | AC 变成泛泛描述 |
| Scenario / AC | 用户场景、Given-When-Then 和可观察验收结果 | Mission、business rules、scope strategy | Interaction、Breakdown、Verify | 验收不可执行 |
| Scope Decision | In / Out / Later / Decision Needed | Mission、risk、dependency | Solution、Breakdown、Delivery | 未授权范围进入实现 |
| Validation Signal | 证明 AC 达成所需的证据类型 | Scenario design | Verify、Code Review | 测试通过但需求无法验收 |

### Interaction

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Surface | 用户可进入或操作的界面 / 导航节点 | PRD、product domain model、project UI patterns | Frontend execution、E2E Review | 页面边界漂移或重复造界面 |
| User Journey | 用户从触发到完成目标的路径 | Scenario、AC、domain action | Prototype、E2E | 只画页面，不证明路径 |
| UI State | loading、empty、error、permission、success、focus 等状态 | domain state、scenario、risk | Frontend、E2E | 交互缺少失败 / 边界状态 |
| Domain-UI Mapping | 业务对象 / 状态 / 动作到界面的映射 | product-domain-model | Solution、Tech Design、Frontend | UI 表达脱离业务语义 |
| E2E Obligation | 用户路径的 locator 和验证义务 | interaction flow | Code Review、Verify | 后续无法用真实路径验证 |

### Solution

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Decision Point | 需要路线选择的关键问题 | PRD、discovery、constraints | Tech Design、Review | 技术设计直接拍脑袋 |
| Candidate Option | 可行候选路线及适用条件 | architecture context、evidence | Decision table | 没有真实 tradeoff |
| Decision / Rationale | 选定路线和取舍理由 | candidate comparison | Tech Design、Breakdown | 下游不知道为什么这样做 |
| Forbidden Path | 明确禁止或不采用的路线 | risk、scope、constraints | Tech Design、Review | 实现绕回已拒绝方案 |
| Mitigation / Gate | 风险缓解或需人工决策点 | risk analysis | Stage Gate、Delivery | 风险被隐藏 |

### Technical Analysis

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Module | 实现职责边界和所属文件 / 包 | solution decision、codebase | Breakdown、Architecture Review | 任务拆分失去边界 |
| Interface Change | API、函数、事件、CLI、schema 等契约变化 | solution、domain model | Execute、Integration Review | 调用方 / 被调方不一致 |
| Data / State Flow | 数据、状态、权限和错误如何流动 | PRD、solution、codebase | Execute、TDD、Verify | 实现只改局部，破坏闭环 |
| Error / Compatibility Strategy | 错误处理、兼容性、回滚、观测策略 | risk、production constraints | Execute、Delivery | 生产风险无处理路径 |
| Verification Strategy | 证明设计正确的测试和证据路径 | AC、risk、module design | Breakdown、Code Review、Verify | 任务完成无法被证明 |

### Agent Capability Design

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Agent Component | 具备独立责任的 Agent / skill / tool / policy 单元 | PRD、solution | Tech Design、Execute、Review | Agent 行为边界不清 |
| Work Rights | 感知、解释、判断、行动、边界、责任六类工作权 | agent capability requirement | Agent implementation、Eval | Agent 只靠 prompt 自律 |
| Enforcement Mechanism | tool permission、hook、policy、runtime guard、eval 等约束机制 | technical design | Code Review、Verify | 约束不可执行 |
| Eval Scenario | 正常、边界、对抗、歧义场景和阈值 | risk、work rights | Agent Eval、Delivery | 无法证明 Agent 能力成立 |

### Breakdown

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Parent Task | 可独立交付的纵切任务 | tech-design、AC | Execute、Stage Gate | 任务切片只按文件或层拆 |
| Atomic Task | Parent task 内可执行的最小实现单元 | implementation strategy | Execute | 子 Agent 无法准确动手 |
| Authorized Path | 可读写文件和边界 | tech-design、ownership | Execute、Review | 越权改动 |
| Stop Condition | 必须停止并回上游决策的条件 | risk、dependency | Execute | 失败时继续猜 |
| Required Evidence | 完成任务必须提交的测试 / 结果证据 | verification strategy | Code Review、Verify | 做完但无法证明 |

### Execute

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Execution Unit | 当前执行的 Atomic Task 和角色 surface | execution-brief | Code Review、Trace | 多做 / 少做 / 跨任务 |
| Red Evidence | 目标行为缺失或缺陷复现的失败证据 | tests、reproduction | TDD Review | 测试不能证明实现有效 |
| Green Evidence | 实现后目标测试通过的证据 | test command | Code Review、Verify | 只声称完成 |
| Changed Surface | 实际改动的模块、接口、UI、数据或配置面 | diff、task brief | Review、Delivery | review 无法聚焦 |
| Regression Evidence | 原路径和相关风险未回归的证据 | focused suite、manual result | Verify | 修复引入新问题 |

### Code Review

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Finding | 可定位、可复现、可修复的问题 | diff、tests、design、AC | Execute fix loop | 审查变成泛泛建议 |
| Severity | High / Med / Low 与是否 HOLD | exploitability、AC impact、risk | Stage Gate | 阻断项被放行 |
| Role Boundary | 该 finding 为什么属于当前 reviewer | reviewer method | Review summary | 审查职责重叠或遗漏 |
| Evidence | 代码位置、命令、场景或报告依据 | diff、toolchain、reports | Fix、Audit | finding 不可验证 |
| Resolution Ref | 修复或接受风险的记录 | follow-up diff、approval | Verify、Delivery | 问题状态不闭环 |

### Verify

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| AC Under Verification | 正在验证的验收项 | product-definition、mission contract | Delivery | 验证不对应需求 |
| Expected Result | 按 AC 应观察到的结果 | PRD、spec | verification report | 只跑命令没有预期 |
| Actual Result | 实际观察到的用户 / 系统结果 | command、browser、API、data | Delivery | 结论无事实基础 |
| Command Evidence | 验证过程实际运行过的命令证据 | terminal / CI | Audit、Stage Gate | 无法复现 |
| Result Evidence | 可观察结果证据 | screenshots、API output、data state | Delivery | 测试通过不等于 AC 通过 |

### Delivery

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Delivered Scope | 实际交付了什么、没有交付什么 | mission、diff、verification | User acceptance | 用户不知道验收范围 |
| Acceptance Item | 用户可逐条验收的项目 | AC、verification | User | 交付包不可自验 |
| How To Verify | 用户可执行的验收步骤 | verification report | User | 只能相信 Agent 口头说明 |
| Known Gap / Risk | 未解决风险、accepted risk、后续项 | review、approval | User、Retrospective | 风险被隐藏 |
| Evidence Link | 指向验证、审查、命令和结果证据 | stage artifacts | Audit | 交付不可追溯 |

### Retrospective

| Element | Definition | Source | Used By | Failure If Missing |
|---|---|---|---|---|
| Planning Delta | 原计划与实际执行偏差 | trace、stage artifacts | process improvement | 只总结情绪，不改系统 |
| Failure Pattern | 可复用的失败模式 | review / verify / gate failures | workflow / prompt updates | 同类问题重复出现 |
| Improvement Proposal | 指向 workflow、hook、schema、prompt 或 methodology 的改进建议 | retrospective analysis | Harness maintenance | 复盘不能落地 |
