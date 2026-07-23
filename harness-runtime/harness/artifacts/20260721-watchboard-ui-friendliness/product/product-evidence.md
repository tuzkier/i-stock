# 产品证据记录：多市场看盘终端（MyInvestment）界面友好化改造

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/product/product-evidence.md`
> **用途**：记录产品定义使用过的项目知识、规格、代码影响分析和降级情况。

**任务编号（mission-id）：** 20260721-watchboard-ui-friendliness
**状态：** `draft`

---

## 控制契约

- 控制契约（程序识别标记：Control Contract: `contracts/prd.contract.yaml`）
- 权威来源：外部 YAML 是程序化权威来源；本文件只记录证据和解释。

---

## 任务输入

| 输入 | 路径 / 来源 | 使用方式 | 结论 |
|------|-------------|----------|------|
| 任务契约（Mission Contract） | `harness-runtime/harness/missions/20260721-watchboard-ui-friendliness/mission-contract.md` | 判断任务就绪、抽取目标/成功定义/US-01~07/SCN-01~07/范围/约束/治理档 | 就绪：目标、用户、场景、成功定义、范围、验证口径清晰且自洽（含 2 轮 mission-contract-effectiveness-reviewer PASS）。无 NEEDS_DECISION |
| 探索简报（Discovery Brief） | 不适用：治理档 `可跳过阶段=[discovery, interaction]`，未产出 discovery-brief | 现状事实由已过审 business-object-analysis 从源码路径直接抽取 | 无 discovery-brief 属治理决策，非缺口；以源码为事实基线 |
| 项目上下文（Project Context） | `project-context.md` | 消费 ARCH-001~003、CODE-001~003、PIT-001~003、技术选择、测试约定 | 确认前端呈现层边界、中文文案约定、fallback 明示与投资边界合规约束、build 作质量检查 |
| 业务对象分析 | `product/business-object-analysis.md`（已过审） | 综合 OBJ-01~09、STM-01~08、BR-01~12、领域状态→呈现语义映射 | 领域基线充分，全部可追溯源码路径 |
| 用例模型 | `product/use-case-model.md`（已过审） | 综合 BUC-01~03、SUC-01~06、SUC-xx-FLOW/OP、UIC-01~07、DEC-01、DMF-01/02、追溯矩阵 | 系统边界与界面承载充分，唯一待定 DEC-01 |
| 验收场景 | `product/acceptance-scenarios.md`（已过审） | 综合 SCN-01~07（22 条件）、NEG-01~07、RC-01~11、验证证据计划 | 验收口径可观察/可量化/可追溯，全部锚定已确认 SUC/BR |
| 范围策略 | `product/scope-strategy.md`（已过审） | 综合 SCOPE-01~18、用例范围闭环、方案路线约束、下游边界 | 范围闭环成立，收缩下限 SCOPE-01~09；唯一 DECISION_NEEDED（SCOPE-10）默认档不阻断 |

---

## 项目知识证据

| 证据 ID | 来源 | 相关主题 | 产品判断影响 | 置信度 |
|---------|------|----------|--------------|--------|
| KE-01 | project-context ARCH-001 | 前端由 Vite/React 承载、后端只做静态服务与行情代理 | 确认改造面限前端呈现层（App.tsx/features/*/styles.css/RestoreStatus.tsx），不触后端 | 高 |
| KE-02 | project-context CODE-001 | 用户可见文案默认中文，金融缩写/代码/指标名可保留英文 | 人话化文案须中文；alertLevel 已是中文档位可直接复用；RSI/MACD/ATR 等可保留 | 高 |
| KE-03 | project-context CODE-003 / PIT-001 | 行情不可用时演示数据必须明确提示、不能伪装真实行情 | demo_fallback（DEC-01）呈现须让用户识别兜底/演示数据——即使定档信息级也不得完全等同 formal 无提示 | 高 |
| KE-04 | project-context PIT-003 / CODE-003 | 技术信号易被误解为交易建议，强买卖/评分文案须保留提醒/技术分析边界 | nonAdvice 免责始终可见列为合规质量约束（RULE-09），折叠/降级不得隐藏 | 高 |
| KE-05 | project-context 技术选择「质量检查=npm run build」 | 当前无独立 test script，build 覆盖 tsc + vite build | EVD-01 build 仅作前提证据，验收以呈现证据（截图/DOM/E2E）为主 | 高 |
| KE-06 | project-knowledge/specs/local-stock-watch-workbench/spec.md（active） | 既有能力规格：多市场自选/工作台/指标/信号功能行为 | 本任务不改这些功能行为，只新增「呈现忠实性」差量能力（watchboard-presentation），二者正交 | 高 |

---

## 规格对齐

| 能力 | 基线规格 | 变更类型 | 对需求 / 场景的影响 | 决策 |
|------|----------|----------|---------------------|------|
| watchboard-presentation（看盘界面呈现/状态色语义/信号可读性） | none（首次建立；相关既有能力 `local-stock-watch-workbench` 提供功能基线上下文） | 新增（ADDED，draft） | 新增「界面忠实、无误导呈现既有领域状态」的行为契约；覆盖 SCN-01~07 呈现义务 | 建立差量规格 `product/specs/watchboard-presentation/spec.md`，标注新增-draft，任务收尾后提炼固化 |
| local-stock-watch-workbench | `project-knowledge/specs/local-stock-watch-workbench/spec.md`（active） | 不变（本任务不改功能行为） | 自选/工作台/信号功能语义不变；呈现改造不得破坏既有功能场景 | 复用为约束基线；E2E 回归须保证既有用户路径不回归（NEG-07） |

---

## 用例建模证据

| 证据 ID | 支撑内容 | 来源 | 支撑的业务用例 / 系统用例 | 判断结果 |
|---------|----------|------|-----------------------------|----------|
| UCE-01 | 来源健康三档分类（正常/信息/异常）是「状态色归位」直接依据 | BR-02；OBJ-02/STM-02；App.tsx:639 | BUC-01 / SUC-01 | 已确认：呈现层可按档分色，不改 domain 判定 |
| UCE-02 | 人话化文案源已存在于源码，无需新建映射表 | ATTR-19 displayLabel、ATTR-24 stanceLabel、ATTR-16 中文 alertLevel、OBJ-07 label/detail、App.tsx:86-93 sourceStatusLabel | BUC-01 / SUC-02、SUC-03 | 已确认：SUC-02/03 人话化优先复用既有可读源 |
| UCE-03 | 恢复态 restored 被 `.data-notice` 复用是误导性黄条直接根因 | BR-10；RestoreStatus.tsx:7-21 | BUC-03 / SUC-06 | 已确认：SUC-06 呈现层归位，不改快照读写 |
| UCE-04 | 跨呈现一致性门控（来源→信号降级）已在 domain 层实现 | BR-03；trade-signals.ts:619-627；操作间依赖表 | BUC-01 / SUC-01→SUC-03 | 已确认：SCOPE-09 一致性呈现层只读承载，不重实现门控 |
| UCE-05 | MTS 极性/档位是「计算分类」非生命周期状态，无独立 STM | DMF-01；BR-04/05 | SUC-02 | 已确认：不虚构新 STM，引用 BR-04 分色 |

## 系统责任澄清

| 问题 | 影响的业务用例 / 系统用例 | 为什么不能假设 | 需要谁确认 | 当前处理 |
|------|---------------------------|----------------|------------|----------|
| DEC-01：demo_fallback 来源色档最终归类（信息级 / 需关注） | BUC-01 / SUC-01（ST-01c、SUC-01-FLOW-02.demo_fallback）；UIC-01 | 源码现状（App.tsx:639 与真异常同级）与 intent-framing（正常态样例未点名 demo_fallback）证据不一致，硬定档会造成「降级可用被当严重故障」或「兜底数据被当正常」两种误导 | acceptance-scenario-designer 依 SCN-01 判定，必要时用户确认 | 明确延后：默认「信息级/次级提示（非高危警告色）」软口径，不阻断；最终档 verify 前经用户确认（SCN-01-COND-02 已给改判口径调整备选） |

---

## Graphify 证据

> 既有项目、现有代码影响、模块边界、调用链或兼容性不确定时必须填写；不可用时写入 Degradations。

| 证据 ID | Graphify 查询 / 输出 | 影响面 | 产品判断 |
|---------|----------------------|--------|----------|
| GN-01 | 不适用（未运行 Graphify） | 呈现层改造影响面已由 business-object-analysis 从源码逐条锚定（`src/App.tsx:639/651-655/532/641/95-97/86-93`、`src/features/restore/RestoreStatus.tsx:7-21`、`src/types.ts`、`src/domain/*`），影响文件集清晰（App.tsx / features/* / styles.css / RestoreStatus.tsx） | 呈现层改造，不改 domain 调用链/状态机；影响面锚定充分，未触发跨模块兼容性不确定，无需图谱补证 |

---

## 影响方案路线的事实与风险

| 事实 / 风险 | 来源 | 影响的用例 / 约束 | 对方案路线的影响 | 证据是否足够 | 不足时怎么处理 |
|-------------|------|-------------------|------------------|--------------|----------------|
| 人话化文案源已存在于源码（displayLabel/technicalReminder/中文 alertLevel/stanceLabel/sourceStatusLabel/MtsReason.label/detail） | RISK-03；ATTR-16/19/24；App.tsx:86-93；OBJ-07 | SUC-02/03；SCOPE-02 | 方案应**优先复用既有可读源**，而非新建枚举→文案映射表——关键决策点 | 足够，原因：源码路径可查、已过审 | 未注册码按 UNKNOWN_CODE 回落（BR-05） |
| 跨呈现一致性门控（来源 stale→信号 source_degraded）已在 domain 层 BR-03 实现 | RISK-04；trade-signals.ts:619-627；操作间依赖表 | SUC-01→SUC-03；SCOPE-09；NEG-01 | 方案须把它作为**呈现忠实读取约束**，不在呈现层重实现门控——关键决策点 | 足够，原因：源码门控逻辑明确 | 呈现层只读 STM-02/05 结果并保持三处一致 |
| 状态色需四档语义分层（正常/信息/谨慎-风险/警告-异常），且 negative 评分与来源故障色物理区分、涨跌红绿与警告色分离 | SCOPE-01；BR-02/04/10；App.tsx:639/95-97；RestoreStatus.tsx | SUC-01/02/06；UIC-01；SCN-01 | 方案须引入语义色分层，不得沿用「非 formal 一律 data-notice」「所有恢复态复用同一黄条」「negative 与来源故障共用告警色」——关键决策点 | 足够，原因：三条 BR 分类明确 + 现状缺陷行号锚定 | 四档色映射见 domain-model「领域状态→呈现语义映射」；落语义分层非具体色值 |
| 折叠/展开交互状态承载归属未定，interaction 阶段治理档 skippable | RISK-02；mission-contract 可跳过阶段；UIC-02/07 | SUC-02/03；SCOPE-02/08 | **折叠交互状态由谁承载**（solution/technical_analysis/execute）是方案关键决策点；折叠义务不得因 interaction 跳过而丢失 | 足够，原因：治理档与 UIC 折叠要求明确 | 方案明确折叠交互承载层；不得假设跳过的 interaction 自动解决 |
| 「友好」「层级差」「突出/弱化」含主观判断（治理档 uncertainty=medium） | RISK-05；mission-contract 治理依据；SCN-05-COND-01 | SUC-03/05；SCN-05 | 不改路线，影响验证证据强度 | 足够，原因：已接受风险 + 双证据锚定策略 | 主观项以 preview 截图 + 样式 DOM 断言双证据锚定 |
| 若改造发现必须改算法/后端/数据才能达成呈现目标 | RISK-06；mission-contract 升级规则；DMF 总体结论「未发现需新增对象/规则」 | 全范围 | 触发升级决策关口，范围可能变更 | 足够（当前未发生：用例/对象分析均判定呈现层可达成） | 停下升级，不擅自扩到算法/后端 |
| demo_fallback 色档（DEC-01）证据不一致 | RISK-01；DEC-01；SCN-01-COND-02 | SUC-01；UIC-01 | 单一来源结局色档，默认信息级软口径推进，不改路线结构 | 不足（证据冲突），但不阻断，原因：默认档足以推进 | verify 前经用户确认定档；不派生硬阻断验收 |

## 不得带入方案阶段的假设

| 假设 | 为什么不能假设 | 影响范围 | 处理方式 |
|------|----------------|----------|----------|
| 「必须新建一张枚举→文案映射表」 | 人话化文案源已存在于源码，新建映射表是重复造轮、且可能与既有语义漂移 | SUC-02/03；SCOPE-02 | 明确排除：默认复用既有可读源；确有缺口（未注册码）按 UNKNOWN_CODE 回落 |
| 「非 formal 一律 data-notice」「所有恢复态复用同一黄条」「negative 与来源故障共用告警色」 | 这正是被改造的现状缺陷根因（App.tsx:639、RestoreStatus.tsx:8、App.tsx:95-97） | SUC-01/02/06；SCN-01 | 明确排除：方案须四档语义色分层，负向评分/恢复正常态/来源故障各自归位 |
| 「折叠交互留给被跳过的 interaction 阶段自动解决」 | interaction 治理档 skippable，可能不产出；折叠义务会因此丢失 | SUC-02/03；UIC-02/07 | 明确排除：方案须指定折叠交互状态承载层 |
| 「在呈现层重新实现来源→信号降级门控」 | 门控已在 domain 层 BR-03 实现，呈现层重实现会双份逻辑漂移、且触碰非目标 domain 语义 | SCOPE-09 | 明确排除：呈现层只读取门控结果并保持三处一致 |
| 「price/涨跌/来源主源固定在某一处」 | 「主源在哪一处」是承载选点决策（交互/方案层），PRD 只固化「计数=1」 | SUC-01/04/05；SCN-03 | 延后：方案/交互消费 UIC-03、DMF-02 时决定选点 |
| 「可修改 src/domain/* 算法/状态机 / 数据源 / 后端 / alibaba 在途策略代码」 | 契约非目标/约束明确禁止；越界破坏既有正确性或超授权 | 全范围 | 明确排除：改动面限呈现层；遇必须改则升级（RISK-06） |

---

## 降级记录

| 缺失证据 | 原因 | 风险 | 补救动作 | 负责人 |
|----------|------|------|----------|--------|
| Graphify 影响面证据 | 未运行 Graphify；本任务为呈现层改造，影响面已由 business-object-analysis 从源码路径逐条锚定（含行号），影响文件集清晰 | 低：呈现层改造不涉及跨模块调用链/状态机变更，兼容性不确定性低 | 若 execute 阶段发现呈现改动触及未预期模块，回流补 Graphify/依赖影响分析 | senior-product-expert → execute |
| 独立自动化 test script | 项目当前无 test script（KE-05），质量检查用 `npm run build` | 中：build 覆盖 tsc + vite build 但不覆盖运行时呈现断言 | 验收以 EVD-02 截图 + DOM 断言 + EVD-03 Playwright E2E + axe 为主，build 仅前提；e2e.enabled 路径由 verify 阶段落实 | verify |
