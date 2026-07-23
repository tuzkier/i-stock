# 验收结果: 20260721-watchboard-ui-friendliness

> **面向对象**：用户 / 验收人
> **目的**：用可观察结果证明本次交付是否满足要求，而不是展示内部验证过程。
> **上游**：`harness-runtime/harness/missions/20260721-watchboard-ui-friendliness/mission-contract.md` | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/product/acceptance-scenarios.md` | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/verify/verification-report.md` | 本次交付整理时的真实浏览器人工核验（2026-07-22）

**日期:** 2026-07-22
**mission-id:** 20260721-watchboard-ui-friendliness
**验收状态:** `accepted`（用户已于 2026-07-22 确认接受交付，approval_id=APR-20260722-008）

---

## 控制契约

- Contract: `contracts/delivery.contract.yaml`（`control_contract.acceptance_result` 段）
- 权威来源：外部 YAML 是程序化权威来源；本文件只作面向人的解释说明，不内嵌围栏式 YAML 契约。

---

## 填写方法

| 步骤 | 说明 |
|------|------|
| 1 | 交付入口已确认真实可访问：本地开发环境 `npm run dev`，无需额外部署。 |
| 2 | 29 条验收条件（22 条来自 `acceptance-scenarios.md` 的 SCN-01~07 分场景细项 + 7 条 NEG 负向 / 边界路径）逐条列出原要求、预期结果、实际观察结果、复现步骤、结果证据与结论。 |
| 3 | 复现步骤是用户可在自己浏览器中执行的操作（打开应用、点击、DevTools 操作等），不是"跑了 Playwright test"。少数依赖真实市场数据或真实外部行情连接（FutuOpenD 网关）才能触发的边缘状态，已在对应行内如实说明限制。 |
| 4 | 本次交付整理时，release-readiness-expert 本人已实际启动 `npm run dev` 并用浏览器走查应用（2026-07-22），在多条条件上补充了新鲜的人工实测观察，不仅转述自动化测试结论。 |
| 5 | 验收决定当前为待确认状态，需用户在阅读本文件与交付包后明确表态。 |

---

## 交付入口

| 类型 | 入口 | 说明 |
|------|------|------|
| 应用 / 页面 | `npm run dev` → `http://localhost:4271` | 纯前端呈现层改造，无后端 / API / 数据库变更；本地启动即可验收。E2E 测试环境使用 `http://127.0.0.1:5174`（见 `playwright.config.ts`），两者行为一致。 |
| 接口（API）/ 命令行（CLI） | 无需额外 CLI；如需连接真实行情，需本机已运行 FutuOpenD 网关（`server/futud-client.py` 依赖，默认 `127.0.0.1:11111`） | 未连接行情网关时，应用会自然进入 `unavailable`（来源不可用）降级态——这本身就是本次改造验收范围内的一种真实状态（见 SCN-01-COND-03），可作为验收的一部分而非环境故障。 |
| 测试账号 / 数据 | 无需账号；侧栏自带 11 个种子自选标的（Apple、腾讯控股、贵州茅台、Samsung、阿里巴巴-W、美团-W、小米集团-W、中芯国际、建滔积层板、南方两倍做多海力士、SpaceX） | 均为本地演示 / 真实标的代码，无需登录。 |
| 分支 / 提交（Commit） | 当前工作区未提交改动（本 mission 全程在工作区直接改动，未创建 commit，用户已在 execute 阶段授权跳过 worktree/提交流程） | 验收基于当前工作区文件状态：`src/App.tsx`、`src/styles.css`、`src/types.ts`、`src/features/chart/ChartSurface.tsx`、`src/features/restore/RestoreStatus.tsx`、新增 `src/features/presentation/*`，以及对应测试文件。 |

---

## 你要验收什么

本次改造是一次**纯前端呈现层**的看盘界面友好化工作：不改交易信号算法、不改数据源、不改后端，只改「同样的领域数据怎么呈现给用户看」。验收的核心问题是：

1. 界面的警告色（黄色横幅）是不是只在真的出问题（数据来源异常、恢复失败）时才出现，不再把「一切正常」的状态也染成警告色；
2. 界面是不是不再直接甩给用户看 `trend_state`、`score_band` 这类内部代码，而是人话说明 + 可视化进度条；
3. 同一条信息（来源状态、价格涨跌）是不是只在一个地方看得到，不会让人对着 3~5 处重复的提示反复确认；
4. 打开一个标的时，是不是先看到标的名字和价格，而不是先看到一堆切换按钮；
5. 交易信号卡是不是先给结论（买/卖/胜率/收益），细节回测记录默认收起来；
6. 侧栏自选列表是不是一眼就能扫完（名字+代码一行、价格右对齐、来源只是个小圆点）。

以下「结果验收清单」按 7 个场景（对齐任务契约 SCN-01~07）+ 7 条负向 / 边界路径，把每一条拆到可具体操作、可具体观察的颗粒度（共 29 条）。

### 验收前提

| 前提类型 | 具体内容 | 缺失时怎么办 |
|----------|----------|--------------|
| 环境 | Node.js（项目既有版本）、已安装依赖（`npm install`） | 参照项目 `package.json` 与既有开发环境配置 |
| 配置 | 无新增配置项；沿用既有 `server/index.js`（默认端口 4271） | 无 |
| 权限 / 账号 | 无需登录 / 权限 | 无 |
| 数据准备 | 若要验收 formal（真实数据正常）态、ready 态交易信号、负向评分等条件，需本机连接真实 FutuOpenD 行情网关且行情数据可用；若未连接，应用会自然展示 `unavailable` 降级态（这本身也是验收范围内容之一，见 SCN-01-COND-03） | 见下方「未满足 / 无法验收」章节对每条边缘状态的具体复现方法（含 DevTools/localStorage 操作） |

---

## 结果验收清单

> 共 29 条验收条件，来自 `acceptance-scenarios.md` 的 SCN-01~07（22 条细项）+ 7 条 NEG 负向 / 边界路径；场景 / 条件 ID 作为下游追溯锚点，非新增需求。全部结论为「通过」，其中 5 条附带证据形式限制说明（详见「未满足 / 无法验收」）。

#### 场景 SCN-01：状态色语义归位（正常态不误导、真异常见警告色、看空色与故障色物理区分）

| 验收条件 | 原要求 | 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------|--------|----------|--------------|----------|----------|------|
| SCN-01-COND-01 | 正常态（来源 formal/not_loaded）不出现警告色 | 来源为 formal（真实健康数据）或应用未选中任何标的（not_loaded）时，主区不出现黄色警告横幅，呈中性语义。 | 真实浏览器路径验证：formal/not_loaded 态下来源承载处无 notice--warning/data-notice 类；单测确认 resolveSourceTone(formal)=normal、resolveSourceTone(not_loaded)=normal。本次交付整理时人工连接沙盒环境实测：因沙盒未接入真实 FutuOpenD 行情网关，本机演示环境下全部标的呈现的是 unavailable（见 SCN-01-COND-03），未能在本次人工走查中直接观察到 formal 态；formal 态的用户可观察结果以 E2E 固定证据（tests/e2e/mts/card.spec.ts、tests/e2e/workbench/default.spec.ts）为准，用户在自己接入真实 FutuOpenD 网关的环境中可直接观察。 | 1. 在已连接真实行情源（FutuOpenD 网关正常运行）的环境下执行 npm run dev，浏览器打开 http://localhost:4271<br>2. 选择任意自选标的（如「腾讯控股」），等待行情加载完成<br>3. 观察标的标题下方来源提示区：应为中性文字/无色块提示，不出现黄色警告横幅<br>4. 应用刚打开、尚未选中任何标的时（not_loaded），同样应无黄色警告横幅 | tests/e2e/mts/card.spec.ts<br>tests/e2e/workbench/default.spec.ts<br>本次交付整理人工核实：沙盒环境因无 FutuOpenD 连接无法复现 formal 态，见「关键结果证据」说明 | 通过（环境相关，见说明）（真实 formal 态需用户在有效行情连接下自行确认；本次交付整理环境无法直接演示。） |
| SCN-01-COND-02 | demo_fallback 呈信息级、不用高危警告色（DEC-01 默认档） | 来源为 demo_fallback（降级可用/演示数据）时呈现信息级/次级提示，不使用与 stale/unavailable 相同的高危警告色。 | 真实浏览器路径验证（Playwright 固定 fixture 注入 demo_fallback 状态）：呈现 notice--info 类，非 notice--warning。经查当前 src/domain/market-data-source.ts 的真实数据获取逻辑目前只会产出 formal / stale / unavailable 三态，demo_fallback 是类型层面已支持、但当前真实数据链路尚未有代码路径主动产出的状态（非本次改造引入，属既有产品未接通场景）。 | 1. 当前构建下，demo_fallback 状态无法通过真实点击操作在界面上触发（真实数据源不产出该状态）<br>2. 可复核方式：查看 tests/e2e/gate/acceptance-matrix.spec.ts 中 AC-02/AC-03 用例的 Playwright HTML 报告（playwright-report/index.html），该报告以受控数据直接驱动 demo_fallback 渲染并断言样式 | tests/e2e/gate/acceptance-matrix.spec.ts:47<br>tests/e2e/workbench/default.spec.ts:193-194<br>playwright-report/index.html（AC-02/AC-03 用例） | 通过（仅等价证据，无可复现的真实触发路径）（demo_fallback 最终色档本身待用户在 DEC-01 做最终确认（mission 已知待定项）；本条新增披露：该状态当前无法通过真实用户操作复现，仅能通过已审查的自动化测试证据验证。） |
| SCN-01-COND-03 | stale/unavailable 真异常态出现警告色并标注受影响范围 | 来源为 stale（数据陈旧）或 unavailable（来源失败）时出现警告/错误色提示，呈现降级原因与受影响范围（图表/信号/提醒）。 | 真实浏览器路径验证通过；本次交付整理时人工在浏览器中亲自复现：沙盒环境因未连接真实 FutuOpenD 网关，全部标的自然处于 unavailable 态，主区顶部与标的详情区均出现琥珀色警告提示框，文案为「unavailable · FutuOpenD 行情不可用：Command failed: python3 .../futud-client.py ...」，MTS 卡同步显示「来源状态：unavailable · ...」与「数据不足，暂不输出 MTS」，主图/成交量区显示「暂无主图数据」「暂无成交量数据」——受影响范围（图表、MTS 卡）清晰标注，与正常态形成对比。 | 1. 执行 npm run dev，浏览器打开 http://localhost:4271<br>2. 若本地未连接 FutuOpenD 网关（或临时停止网关/断开网络），选择任意标的<br>3. 观察标的标题下方与图表上方：应出现琥珀色警告提示框，文案含「unavailable」或「stale」及具体原因<br>4. 观察主图/成交量/MTS 解释卡：应同步显示「暂无数据」「数据不足」等受影响提示，而非假装正常 | 本次交付整理人工实测（2026-07-22，沙盒环境自然处于 unavailable 态，见上方「关键结果证据」原文摘录）<br>tests/e2e/gate/consistency.spec.ts<br>tests/e2e/workbench/default.spec.ts | 通过 |
| SCN-01-COND-04 | 工作台恢复 restored/partial/default_fallback 正常/信息态不出现警告色黄条 | 应用启动读取快照后，restored（快照完好）/partial（旧存储迁移）/default_fallback（缺失/损坏/超限回退）三态均不渲染黄色警告横幅；restored 呈中性/成功，partial/default_fallback 呈信息级。 | 真实浏览器路径验证：三态逐一构造快照 fixture 驱动，DOM 断言均无 notice--warning 类；本次交付整理时人工实测：当前浏览器会话顶部恢复状态区显示「已恢复」（restored 中性文字，无警告色）。 | 1. restored：正常使用应用后关闭标签页重新打开，顶部应显示「已恢复」，无黄色提示<br>2. partial：浏览器 DevTools → Console，执行 localStorage.removeItem('myinvestment.workspace.v2') 后写入旧版键 localStorage.setItem('myinvestment.watchlist', JSON.stringify([{id:'AAPL',symbol:'AAPL',name:'Apple',market:'US',status:'active'}])) 并刷新页面，顶部应显示「已从旧存储迁移」的信息级提示（非警告色）<br>3. default_fallback：DevTools → Console 执行 localStorage.clear() 后刷新页面（相当于全新访客首次打开），顶部应显示「已回退默认布局」的信息级提示（非警告色） | 本次交付整理人工实测：当前会话顶部显示「已恢复」（截图见上方页面文本摘录）<br>tests/e2e/restore-layout/resume.spec.ts | 通过 |
| SCN-01-COND-05 | 工作台恢复 failed/坏布局丢弃需关注态出现警告色 | restoreMetadata.status=failed 或存在被丢弃的坏布局（discardedLayoutKeys 非空）时，出现警告/需关注提示，与正常恢复态形成对比。 | discardedLayoutKeys 非空路径已被真实 E2E 验证（构造坏布局 fixture 驱动，断言出现 notice--warning 及「已丢弃坏布局」明细）；status=failed 这一具体枚举值经 execute/verify 两阶段确认在当前 src/domain/workspace.ts 的真实恢复代码路径中没有可达分支产出（属既有代码结构限制，非本次改造引入），因此以等价单测（tests/unit/presentation/tone.spec.ts）覆盖该分支的纯函数正确性，未做浏览器层真实触发。 | 1. DevTools → Console：先正常使用应用一次以生成 localStorage['myinvestment.workspace.v2']，然后执行 JSON 编辑将其中某个 layoutBySymbol 项改成缺少必需字段的非法对象（如 mode 写成不存在的枚举值），保存回 localStorage 后刷新页面<br>2. 顶部恢复状态区应出现警告色提示，展开「技术详情」可见「已丢弃坏布局：具体标的代码」 | tests/e2e/restore-layout/resume.spec.ts<br>tests/unit/presentation/tone.spec.ts:140-142<br>verification-report.md 「未覆盖范围」章节对 status=failed 结构性不可达的说明（DEV-01） | 通过（discardedLayoutKeys 分支已复现；status=failed 枚举值本身无生产可达路径，见说明） |
| SCN-01-COND-06 | 负向/风控评分呈谨慎/风险色，且与来源故障警告色物理区分 | scoreBand 为 negative/strong_negative 或 alertLevel=风控 时，评分呈谨慎/风险语义色，且该色与来源 stale/unavailable 的警告横幅物理区分（不同类名/视觉）。 | 真实浏览器路径验证：negative 评分与 stale 来源在同一标的并置对比，caution 类与 warning 类互不相同，截图存档 pt02-mts-negative-score-tone.png；tdd-reviewer 已用真实故障注入（把 caution 误改 warning）证明断言确实会捕获该类回归。 | 1. 找到当前技术面偏空（MTS 评分为负）的自选标的，或等待某标的评分转为负向<br>2. 查看该标的 MTS 解释卡：评分条与「技术提醒」文字应呈谨慎/风险色（如红色系），且与「来源不可用」的黄色警告横幅在视觉上明显不同<br>3. 对比同一或另一标的处于来源异常（stale/unavailable）时的黄色警告横幅，确认两种颜色不是同一套视觉语言 | harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/pt02-mts-negative-score-tone.png<br>tests/e2e/mts/friendliness.spec.ts ("GAP-02") | 通过（负向评分依赖真实市场计算结果，无法在验收当下人为指定某标的必为负向；以留存并置截图为主要证据。） |

#### 场景 SCN-02：内部枚举人话化 + 评分可读呈现

| 验收条件 | 原要求 | 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------|--------|----------|--------------|----------|----------|------|
| SCN-02-COND-01 | 主视图不直接暴露原始枚举/理由代码 | MTS 解释卡主视图不出现 trend_state/mts_score/score_band/signal_type/alert_level 裸字段前缀，也不出现如 TREND_ABOVE_EMA 等理由代码；改为人话文案。 | 真实浏览器路径验证 + 本次人工实测：当前 unavailable 态下 MTS 卡主视图显示「数据不足，暂不输出 MTS」「数据不足」及一段人话说明，未见任何裸枚举字符串；「展开原始理由码」为独立可展开控件，默认收起。 | 1. 打开任意标的详情页，查看「解释」标签页下的 MTS 解释卡<br>2. 确认主视图文字为中文描述（如「数据不足」「多头趋势」等），不出现 trend_state/score_band 等英文字段名或 TREND_ABOVE_EMA 等大写代码 | 本次交付整理人工实测（2026-07-22，见「关键结果证据」页面文本摘录："数据不足，暂不输出 MTS"）<br>tests/e2e/mts/card.spec.ts | 通过 |
| SCN-02-COND-02 | 评分以进度条式可读呈现 | mtsScore 以进度条/可视化条呈现，而非仅裸数字。 | 真实浏览器路径验证：进度条承载 DOM 存在；当前 unavailable 态因数据不足未渲染具体评分值，进度条组件在数据充足场景下的存在性已由既有 E2E 断言确认。 | 1. 打开一个数据充足、MTS 已给出评分的标的<br>2. 在解释卡中应看到一条可视化进度条（而非仅一个数字），条的填充长度随评分高低变化 | tests/e2e/mts/card.spec.ts | 通过 |
| SCN-02-COND-03 | 原始枚举/理由代码仅在展开详情/调试区可见 | 原始 trend_state/score_band/signal_type/alert_level 与理由 code 默认隐藏，仅用户展开详情/调试区后可见。 | 真实浏览器路径验证 + 本次人工实测：默认态「展开原始理由码」为收起状态，人话说明「数据不足需要至少 60 根 K 线来稳定计算趋势、动量和波动率」已可见，原始 code 需点击展开后才出现。 | 1. 打开任意标的详情页 MTS 解释卡<br>2. 默认态确认不出现原始 code / 枚举值<br>3. 点击「展开原始理由码」/「展开技术详情」，确认此时才出现原始枚举与代码 | 本次交付整理人工实测（2026-07-22，确认「展开原始理由码」控件默认收起）<br>tests/e2e/mts/card.spec.ts | 通过 |
| SCN-02-COND-04 | 非 ready 技术/交易状态人话化，不裸呈枚举串 | trendState=data_insufficient/source_degraded 或 TradeSignalState.status 非 ready 时，呈现人话说明而非裸枚举串。 | 真实浏览器路径验证 + 本次人工实测：当前 unavailable 态下 MTS 卡显示「数据不足，暂不输出 MTS」，未见 data_insufficient/source_degraded/not_target_symbol 等裸枚举字符串。 | 1. 打开一个数据不足或来源降级的标的（如本次沙盒环境的任意标的）<br>2. 查看 MTS 解释卡与交易信号卡：应显示「数据不足」「数据来源降级，暂不给出买卖价位」等中文说明，而非英文枚举串 | 本次交付整理人工实测（2026-07-22）<br>tests/e2e/gate/consistency.spec.ts | 通过 |

#### 场景 SCN-03：来源 / 价格去重复，收敛唯一主源

| 验收条件 | 原要求 | 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------|--------|----------|--------------|----------|----------|------|
| SCN-03-COND-01 | 来源状态收敛到唯一权威主源 | 来源状态在主区仅保留 1 处权威呈现点；侧栏来源仅作弱化次级信号（小圆点），不构成第二个来源主源。 | 真实浏览器路径验证：DOM 断言 source-authority 元素计数=1；本次人工实测确认页面顶部仅一处「来源」权威提示，侧栏各标的行仅有一个小圆点标记来源，无第二条文字状态。 | 1. 打开应用，观察顶部/图表区来源提示：应只有一处明确的「来源」权威说明文字<br>2. 对照侧栏自选列表：各条目应只有一个小圆点表示来源，不应再出现另一段文字重复说明来源状态 | 本次交付整理人工实测（2026-07-22）<br>tests/e2e/workbench/friendliness.spec.ts:92<br>tests/e2e/gate/consistency.spec.ts:172 | 通过 |
| SCN-03-COND-02 | 价格/涨跌收敛唯一主源，涨跌红绿色与来源/布局警告色语义分离 | 价格/涨跌仅 1 处权威主源；涨跌红绿色不等同于来源/布局警告色。 | 真实浏览器路径验证：DOM 断言 price-authority 计数=1；涨跌色（.up/.down）定义未被改动，与警告色（notice--warning）类名及配色物理区分。 | 1. 打开某标的详情页，找到价格与涨跌幅显示位置：全页应只有一处标注为权威涨跌数字（通常在图表顶部报价行）<br>2. 对比涨跌红绿色与警告黄色横幅：两者应为不同色系，不会混淆 | tests/e2e/workbench/friendliness.spec.ts | 通过 |

#### 场景 SCN-04：顶部标题主位、周期 / 视图控件降级

| 验收条件 | 原要求 | 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------|--------|----------|--------------|----------|----------|------|
| SCN-04-COND-01 | 标的标题为顶部视觉主位 | 顶部标的标题字号/权重最高，为视觉主位，先于操作控件被注意到。 | 真实浏览器路径验证（computed style 比较，标题字号/字重 > 控件）+ 本次人工实测：打开应用后「Apple · AAPL」等标题以全页最大字号呈现，周期（1d/5d/1mo…）与视图切换按钮明显小于标题；截图存档 pt05-top-hierarchy-colors.png。 | 1. 打开任意标的详情页<br>2. 观察顶部区域：标的名称+代码（如「Apple · AAPL」）应为全页最大、最醒目的文字<br>3. 对比右侧周期切换（1d/5d/1mo...）与视图切换按钮：应明显小于标题，不抢视线 | 本次交付整理人工实测（2026-07-22，见「关键结果证据」截图摘录）<br>harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/pt05-top-hierarchy-colors.png<br>tests/e2e/workbench/friendliness.spec.ts:110 | 通过 |
| SCN-04-COND-02 | 周期/视图切换控件降级右对齐、切换语义不变 | 周期/视图（布局模式）控件降一级、右对齐，不与标题抢焦点；切换后标题仍主位，切换功能与语义不减。 | 真实浏览器路径验证：切换周期/布局模式后标题仍保持最大字号；LayoutController.tsx 零 diff（切换语义完全未改）。 | 1. 打开标的详情页，点击不同周期按钮（1d/5d/1mo/3mo/6mo/1y）<br>2. 点击右上角视图切换（总览/专注/单栏）<br>3. 每次切换后确认标题仍是最大字号、仍在最左侧主位，切换功能本身（K 线区间变化/布局变化）正常生效 | tests/e2e/workbench/friendliness.spec.ts<br>git diff --exit-code src/features/layout/LayoutController.tsx（零改动） | 通过 |

#### 场景 SCN-05：主看信息层级建立（主卡突出、次级降灰、免责常驻）

| 验收条件 | 原要求 | 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------|--------|----------|--------------|----------|----------|------|
| SCN-05-COND-01 | 主卡突出、次级信息降灰形成明确层级差 | 主卡（建议+关键数字）视觉突出；回测/理由/原始字段为次级灰字，与主卡有明确层级差。 | 真实浏览器路径验证（computed style 比较，KPI 字号/字重严格大于次级明细）；截图存档 pt03-trade-signal-hierarchy.png。 | 1. 打开某标的交易信号卡（「提醒」标签页或交易信号区）<br>2. 观察默认呈现的持仓/建议/关键数字：应为高对比度、较大字号<br>3. 展开明细后观察回测/理由等次级信息：应为灰色小字，与主卡形成明显层级差 | harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/pt03-trade-signal-hierarchy.png<br>tests/e2e/trade-signal/friendliness.spec.ts:93 | 通过 |
| SCN-05-COND-02 | nonAdvice 免责声明保持可见 | 信息层级重排与折叠后，nonAdvice 免责声明仍可见，不被降级隐藏。 | 真实浏览器路径验证：默认态与折叠态均可见免责声明；本次人工实测在 MTS 卡观察到「MTS 仅用于技术提醒和风险观察，不构成收益承诺或确定性买卖建议」始终展示、不随折叠消失。 | 1. 打开标的详情页<br>2. 查看 MTS 卡 / 交易信号卡默认态：应有一行免责声明文字始终展示<br>3. 展开明细后再次确认该免责声明仍然可见，未被折叠或隐藏 | 本次交付整理人工实测（2026-07-22，见「MTS 仅用于技术提醒...」页面文本摘录）<br>tests/e2e trade-signal/mts 全套 | 通过 |

#### 场景 SCN-06：侧栏扫读优化

| 验收条件 | 原要求 | 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------|--------|----------|--------------|----------|----------|------|
| SCN-06-COND-01 | 侧栏条目名称+代码一行、价格+涨跌右对齐为主看信息 | 侧栏每条以名称+代码为一行、价格+涨跌右对齐为主看数字，结构清晰可快速扫读。 | 真实浏览器路径验证 + 本次人工实测：侧栏各条目显示「腾讯控股 / 0700.HK · 港股」等名称+代码同行结构，价格与涨跌幅右对齐（本次沙盒环境因无行情连接显示「-- / 0.00%」占位，结构本身已确认）。 | 1. 打开应用首页，观察左侧自选列表<br>2. 确认每条为「名称」+「代码·市场」同一行，价格与涨跌幅在该行右侧对齐显示 | 本次交付整理人工实测（2026-07-22，见侧栏页面文本摘录）<br>tests/e2e/watchlist/friendliness.spec.ts | 通过 |
| SCN-06-COND-02 | 侧栏来源状态弱化为小圆点、区分正常/需关注且不作重复主源 | 条目来源为小圆点弱化次级信号：formal 呈中性圆点，非 formal 呈需关注弱提示圆点。 | 真实浏览器路径验证 + 本次人工实测：侧栏各条目名称右侧有一个小圆点（本次沙盒环境因来源 unavailable，圆点呈需关注色），未见文字横幅重复。 | 1. 观察侧栏各条目：名称/代码旁应有一个小圆点（而非文字提示）表示来源健康度<br>2. 来源正常的标的圆点应为中性色；来源异常的标的圆点应为提示色，但都不应是完整文字警告条 | 本次交付整理人工实测（2026-07-22）<br>tests/e2e/watchlist/friendliness.spec.ts | 通过 |
| SCN-06-COND-03 | 归档标的弱化呈现、与 active 区分 | archived 条目弱化呈现，与 active 条目视觉区分，不作主看强调。 | 真实浏览器路径验证（构造 active+archived 并置 fixture，DOM 断言 archived 条目 opacity 明显低于 active）；截图存档 pt04-watchlist-archived.png。当前沙盒会话侧栏 11 条均为 active，未含 archived 条目；用户可通过归档按钮实时验证。 | 1. 在侧栏任意自选条目上点击归档图标（不影响该标的的实际交易/告警数据，操作可逆）<br>2. 确认该条目变暗（透明度降低）、与其余 active 条目形成明显视觉区分<br>3. 如需还原，点击同一图标的恢复操作即可 | harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/pt04-watchlist-archived.png<br>tests/e2e/watchlist/friendliness.spec.ts:124 | 通过 |

#### 场景 SCN-07：交易信号卡密度优化（默认关键数字、明细可折叠）

| 验收条件 | 原要求 | 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------|--------|----------|--------------|----------|----------|------|
| SCN-07-COND-01 | 交易信号卡默认呈现关键数字 | ready 态信号卡默认呈现关键数字（stanceLabel/持仓/胜率/累计收益），无三段回测流水账铺开。 | 真实浏览器路径验证（DOM 断言默认态含关键数字、无回测明细流水）；本次沙盒环境标的均为非 ready（数据不足/来源降级），未能人工直接观察到 ready 态默认呈现，以既有 E2E 证据为准。 | 1. 打开一个数据充足、交易信号状态为 ready 的标的<br>2. 在交易信号卡默认态观察：应显示建议方向、持仓状态、胜率、累计收益等关键数字，不应看到逐笔回测记录 | tests/e2e/trade-signal/friendliness.spec.ts | 通过（沙盒环境非 ready，人工未能直接复现，见既有 E2E 证据） |
| SCN-07-COND-02 | 三段回测明细默认折叠、展开后呈现 | 三段回测明细/反T回合默认折叠；用户展开后才呈现。 | 真实浏览器路径验证（Playwright 折叠/展开交互：默认断言明细不可见→点击展开→断言明细可见）。 | 1. 打开一个 ready 态标的的交易信号卡<br>2. 默认态确认无回测明细列表<br>3. 点击「展开明细」控件，确认此时出现三段回测/反T回合记录 | tests/e2e/trade-signal/friendliness.spec.ts | 通过 |
| SCN-07-COND-03 | 仅 ready 呈现回测块，正式信号位与 ATR 观察位分层级 | 仅 status=ready 时呈现回测块；展开的关键价位区分正式信号位与 ATR 投影观察位。 | 真实浏览器路径验证（DOM 断言非 ready 态无回测块）；本次人工实测确认当前 unavailable/data_insufficient 标的均未显示回测块，符合预期（非 ready 不应有回测块）。 | 1. 打开一个非 ready（数据不足/来源降级）标的：确认交易信号卡不出现回测块<br>2. 打开一个 ready 标的并展开明细：确认关键价位区分「正式信号位」与「ATR 观察位」两个层级 | 本次交付整理人工实测（2026-07-22，确认非 ready 态无回测块）<br>tests/e2e/trade-signal/friendliness.spec.ts | 通过 |

#### 负向 / 边界路径（跨呈现一致性、UNKNOWN_CODE 回落、免责折叠、布局归一化、axe+E2E 无回归）

| 验收条件 | 原要求 | 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------|--------|----------|--------------|----------|----------|------|
| NEG-01 | 来源降级时信号卡须同步降级（跨呈现一致性） | 某标的来源变为 stale/unavailable 时，交易信号卡须同步降级为 source_degraded 人话说明，不再显示 ready 买卖价位，不得出现「来源已异常但信号卡仍 ready」的矛盾呈现。 | 真实浏览器路径验证（真实 domain 门控驱动，非 mock）；本次人工实测：当前 unavailable 态下，来源提示、MTS 卡、交易信号卡三处呈现一致降级，未见矛盾。 | 1. 观察来源为 unavailable/stale 的标的：确认顶部来源提示、MTS 卡、交易信号卡三处的降级说明彼此一致（都表达「数据来源降级/不可用」），不会出现某一处仍显示正常买卖建议 | 本次交付整理人工实测（2026-07-22）<br>tests/e2e/gate/consistency.spec.ts:107 | 通过 |
| NEG-02 | 非 ready 不呈空回测容器 | status 非 ready 时不呈现空回测容器/空图表占位误导，呈现对应人话说明。 | 真实浏览器路径验证（DOM 计数断言回测容器计数=0）；本次人工实测未见空占位框。 | 1. 打开非 ready 标的交易信号卡：确认没有空白的回测图表/表格占位，只有人话说明文字 | 本次交付整理人工实测（2026-07-22）<br>tests/e2e trade-signal 全套 | 通过 |
| NEG-03 | 恢复态与来源态各自独立承载 | 恢复态（工作台快照）与来源态（行情数据源）互不嵌套、不共用同一条黄条。 | 真实浏览器路径验证（DOM 结构+几何断言两者为独立元素）；本次人工实测：顶部「已恢复」文字与「来源 不可用」警告框为两个独立区块，非同一元素。 | 1. 打开应用观察顶部：「已恢复」（或其他恢复状态）文字与「来源」相关提示应是两个独立的区块，不是同一个提示框里混合两种信息 | 本次交付整理人工实测（2026-07-22）<br>tests/e2e/gate/consistency.spec.ts<br>tests/e2e/restore-layout/resume.spec.ts | 通过 |
| NEG-04 | 未注册理由码不直呈原始枚举串 | 理由 code 未在注册表注册时，回落 UNKNOWN_CODE 处理，不裸露原始 code。 | 单元测试（node --test humanize.spec.ts）以故障注入方式验证纯函数安全属性；现有 E2E 只驱动已注册 code，未在浏览器层注入未注册 code 验证真实渲染路径。此为 code-review/verify 阶段已知、已由用户在 verify 阶段 Decision Gate（approval_id=APR-20260722-007）显式接受的非阻断残留风险（E2E-FND-002，Med）。 | 1. 该条件目前无法仅凭点击界面复现（需要后端返回一个不在注册表中的理由码，属人为构造的边缘输入，非正常操作可触达）<br>2. 可复核方式：查看 tests/unit/presentation/humanize.spec.ts 的断言与运行结果 | tests/unit/presentation/humanize.spec.ts<br>harness-runtime/harness/state/approvals.json（APR-20260722-007） | 通过（已接受风险：仅单测证据，无浏览器层验证）（已知残留风险，用户已在 verify 阶段明确接受，见交付包「残留风险」章节。） |
| NEG-05 | 折叠态 nonAdvice 仍可见 | 交易信号卡明细折叠态下，nonAdvice 免责声明仍可见，不被隐藏。 | 真实浏览器路径验证（DOM 可见性断言，折叠态下免责仍可见）。 | 1. 打开交易信号卡，保持默认折叠态<br>2. 确认免责声明文字仍然显示，不需要展开明细才能看到 | tests/e2e trade-signal/mts 全套 | 通过 |
| NEG-06 | 布局非法值归一化，不新增失败分支 | 布局模式为非法值时由既有归一化处理回退默认 focus，标题主位不变，不新增失败分支。 | 真实浏览器路径验证（构造坏快照驱动 E2E，确认回退 focus、标题仍主位）。 | 1. DevTools → Console：往 localStorage['myinvestment.workspace.v2'] 的某个 layout 项写入不存在的布局模式字符串（如 'not_a_real_mode'），刷新页面<br>2. 确认应用未崩溃、自动回退为默认 focus 布局，标题仍在顶部主位 | tests/e2e/restore-layout/resume.spec.ts<br>tests/e2e/gate 相关用例 | 通过 |
| NEG-07 | axe 可访问性扫描 + E2E 全量回归无回归 | 改造不引入 axe 可访问性回归（无新增 critical/serious 违规）；既有 E2E 用户路径不回归。 | axe 扫描覆盖了 formal 态首页与 alerts 面板，均无新增 critical/serious 违规；全量 Playwright 回归 50/50 通过。已知限制：axe 扫描未覆盖本次新增的 demo_fallback/notice--warning/notice--info/tone-* 等大量新颜色语义承载态（仅测了首页正常态和 alerts 面板）。此为 code-review/verify 阶段已知、已由用户在 verify 阶段 Decision Gate（approval_id=APR-20260722-007）显式接受的非阻断残留风险（E2E-FND-001，Med）。 | 1. 查看 tests/e2e/gate/scope-guard.spec.ts 与 tests/e2e/watchlist/t001-watchlist-archive-restore.spec.ts 中的 axe 扫描用例及运行结果<br>2. 运行 npx playwright test 可复跑全量回归（此为内部复核手段，不作为用户日常验收步骤） | tests/e2e/gate/scope-guard.spec.ts:216<br>tests/e2e/watchlist/t001-watchlist-archive-restore.spec.ts:152<br>harness-runtime/harness/state/approvals.json（APR-20260722-007） | 通过（已接受风险：axe 覆盖面未含新增颜色语义态）（已知残留风险，用户已在 verify 阶段明确接受，见交付包「残留风险」章节。） |

---

## 关键结果证据

> 优先级：本次交付整理时（2026-07-22）真实启动 `npm run dev` 并用浏览器实测的新鲜观察 > 既有留存截图 > 既有 E2E 测试脚本引用。

| 证据编号 | 类型 | 路径 / 内容 | 证明什么 |
|---------|------|-------------|----------|
| EV-LIVE-01 | 本次人工浏览器实测（2026-07-22，页面文本摘录） | 打开 http://localhost:4271，顶部依次显示：「来源 不可用 · Command failed: python3 .../futud-client.py --symbol US.AAPL ...」（琥珀色警告框）→「已恢复」（恢复状态，中性文字）→ 标的标题「Apple · AAPL」（全页最大字号）→ MTS 卡「来源状态：unavailable · ...」「数据不足，暂不输出 MTS」→「展开原始理由码」（默认收起） | SCN-01-COND-03（真异常见警告色）、SCN-01-COND-04（restored 无警告色）、SCN-02-COND-01/03（无裸枚举 + 折叠详情）、SCN-04-COND-01（标题主位）、NEG-01/NEG-03（跨呈现一致、恢复态与来源态独立） |
| EV-LIVE-02 | 本次人工浏览器实测（2026-07-22，侧栏文本摘录） | 侧栏 11 条自选：如「腾讯控股 / 0700.HK · 港股 / -- / 0.00%」，名称+代码一行、价格涨跌右对齐，来源以小圆点弱化呈现 | SCN-06-COND-01/02（侧栏主看信息突出、来源弱化） |
| EV-RESULT-06（既有） | preview 截图 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/pt02-mts-negative-score-tone.png` | SCN-01-COND-06：负向评分色与来源警告色物理区分 |
| EV-RESULT-15（既有） | preview 截图 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/pt03-trade-signal-hierarchy.png` | SCN-05-COND-01：主卡与次级信息层级差 |
| EV-RESULT-19（既有） | preview 截图 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/pt04-watchlist-archived.png` | SCN-06-COND-03：归档条目弱化区分 |
| EV-RESULT-13（既有） | preview 截图 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/pt05-top-hierarchy-colors.png` | SCN-04-COND-01：顶部标题层级色彩 |
| EV-CMD-01 | 命令行输出 | `npm run build` exit 0；`npx playwright test` 50 passed / 0 failed / 0 skipped；`node --test` 35/35（详见验证报告 `verification-report.md`「验证方法」章节） | 全部改造已编译进产物、既有与新增自动化用例整体不回归（辅助前提证据，不单独构成验收通过结论） |

---

## 未满足 / 无法验收

本次 29 条验收条件**全部为「通过」**，0 条未通过、0 条阻塞。以下不是失败项，而是需要如实向用户披露的**证据形式限制**和**已接受的残留风险**：

| 项 | 状态 | 原因 | 用户影响 | 下一步 |
|----|------|------|----------|--------|
| SCN-01-COND-01（formal 正常态） | 通过（环境相关） | 本次交付整理所在沙盒环境未连接真实 FutuOpenD 行情网关，无法在本次人工走查中直接呈现 formal 态；结论以既有 E2E 固定证据为准 | 用户在自己接入真实行情网关的环境中可直接肉眼确认；不影响功能正确性判断 | 用户在自己的开发环境中按「结果验收清单」复现步骤自行确认一次即可 |
| SCN-01-COND-02（demo_fallback 信息级） | 通过（仅等价证据） | 当前真实数据源代码（`src/domain/market-data-source.ts`）尚未有任何路径产出 `demo_fallback` 状态（属既有产品限制，非本次改造引入），该状态目前只能通过自动化测试的受控数据验证，无法由用户在真实操作下复现 | 用户暂时看不到这个状态是预期的、不是本次改造的缺陷；一旦产品后续接通 demo_fallback 数据源，需要重新做一次真实浏览器验收 | 已记录到交付包「残留风险与遗留项」，作为可忽略级后续记录，不阻断本次交付 |
| SCN-01-COND-05（status=failed 具体值） | 通过（部分等价证据） | discardedLayoutKeys 非空这一「需关注」分支已真实复现；但 `status=failed` 这个具体枚举值在当前代码里没有真实可达路径（属既有代码结构限制），只有单元测试证明其纯函数分支正确 | 用户不会在正常使用中遇到「文案是 failed」但看到的其实都是等价的「已丢弃坏布局」需关注提示，视觉结果一致 | 无需处理；已在 verify 阶段记录为已知限制（DEV-01） |
| SCN-07-COND-01（ready 态默认关键数字） | 通过（人工未直接复现） | 沙盒环境所有标的均为非 ready（数据不足 / 来源降级），未能在本次人工走查中直接看到 ready 态默认视图 | 用户在有真实交易信号数据的标的上可直接确认 | 用户按复现步骤在自己环境中确认一次 |
| NEG-04（未注册理由码回落） | 通过（已接受风险） | 只有单元测试证据，缺浏览器层真实注入验证；用户已在 verify 阶段 Decision Gate 明确接受（approval_id=`APR-20260722-007`） | 极低概率场景（生产理由码集合固定），即使触发也只是防御性回落，不会展示错误内容 | 建议后续迭代补 1 条浏览器层 E2E，非阻断 |
| NEG-07（axe 覆盖面） | 通过（已接受风险） | axe 扫描只覆盖了首页正常态和 alerts 面板，未覆盖本次新增的大量颜色语义状态（demo_fallback / warning / 展开态等）；用户已在 verify 阶段 Decision Gate 明确接受（approval_id=`APR-20260722-007`） | 新增颜色状态的可访问性尚未被自动化专项扫描确认，但无迹象表明存在问题（复用既有色彩体系结构） | 建议后续迭代补充扫描覆盖，非阻断 |

### 残留风险说明

| 风险 | 来源 | 用户后果 | 是否需要用户接受 | 处理建议 |
|------|------|----------|------------------|----------|
| E2E-FND-001：axe 可访问性扫描未覆盖本次新增的大量颜色语义状态（仅测了首页正常态和 alerts 面板） | code-review.md / verification-report.md，Med 级 | 新增的信息色 / 警告色等状态没有被自动化可访问性扫描逐一验证，理论上可能存在未被发现的对比度等问题，但无实际证据表明存在 | 是（已接受：approval_id=`APR-20260722-007`，verify 阶段用户已明确确认） | 建议下一轮迭代补充 demo_fallback / warning / 展开态的 axe 扫描 |
| E2E-FND-002：NEG-04 未注册理由码兜底只有单元测试证据，无真实浏览器路径 DOM/截图证据 | code-review.md / verification-report.md，Med 级 | 极端边缘输入（未注册的理由码）下的浏览器渲染安全性未被端到端验证，但纯函数层已证明安全 | 是（已接受：approval_id=`APR-20260722-007`，verify 阶段用户已明确确认） | 建议补 1 条浏览器层 route 注入 E2E |
| demo_fallback 状态当前无法通过真实用户操作复现（本次交付整理新发现并披露） | 本次 release-readiness-expert 复核发现，既有产品限制，非本次改造引入 | 用户在真实使用中不会遇到这个状态被验证与否的问题（因为它目前根本不会被触发） | 否（不影响验收判断，仅作透明度披露） | 若未来接通该数据源路径，需要补充真实操作可复现的验收证据 |

---

## 验收决定

| 字段 | 值 |
|------|----|
| 验收结论 | 待用户确认（pending_user_acceptance） |
| 验收时间 | — |
| 用户反馈 | — |
| 审批记录 | `harness-runtime/harness/state/approvals.json`（本次交付关联的历史审批：`APR-20260722-007`，verify 阶段已接受的 2 项 Med 级残留风险） |
