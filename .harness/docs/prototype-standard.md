# 交互原型设计标准（interactive_prototype）

> 适用：`prototype.delivery_mode=interactive_prototype`（默认路线）的交互阶段长期可操作原型。
> 定位：本文是"原型怎么搭"的权威标准，被 `interaction` 技能、`interaction-designer` / `interaction-reviewer` Agent、演示导览播放器 `harness-prototype-frame.html` 模板和 `harness interaction prototype-check` 对账命令共同引用。
> 不适用：`frontend_engineering` 路线（见 `prototype-as-frontend` 技能）。
> 完整模型与对账规格见 `docs/prototype-stage-coverage-redesign.md`。

## 一句话原则

**原型是「行为图（behavior graph）⊗ 布局骨架（layout skeleton）」的可视化实现**：行为图把每个 SUC 的每条 flow 拆成「拍（step）= 流步骤 × 结局状态」并用「边（edge）= 真实触发」连成路径，定义**有哪些态、怎么流转**；布局骨架（surface-model 的区域树）定义**页面怎么排**——把每个 surface 切成区域（region），规定嵌套、排布、主次和扫描动线。原型把每个拍对应的 **page-state（页面态）** 按区域树渲染成可操作的静态块、把每条边接成真实操作，并让每个可见对象落到它声明的区域里。原型不是状态快照墙，不是数据驱动的运行时渲染应用，**也不是把控件随意堆在一起的画布**——没有布局骨架，写出来的就是控件乱堆。

## 概念分层（与 lint 颗粒一致）

| 层 | 是什么 | 在原型里 |
|----|--------|----------|
| SUC | 一个参与者目标 + 全部 flow | 导航树第 1 层 |
| flow | 一条路径（主/备选/异常） | 导航树第 2 层 |
| step（拍） | 流步骤 × 结局状态 = 覆盖颗粒 | 导航树第 3 层；锚 `data-step` |
| page-state（页面态） | surface × 状态的渲染原子 | 一个 `data-state` 态块；锚 `data-pagestate` |
| edge（边） | 到达一个态的真实触发 | 真实控件 / 产品输入；system_event 锚 `data-via` |
| region（区域） | surface 内的布局槽位（组成轴） | 区域容器；锚 `data-region`；定义在 surface-model 布局骨架机器段 |

手写真相源有两处，分属两轴：
- **行为轴** `interaction-spec/behavior-graph.yaml`（page_states/steps/edges/flows）——有哪些态、怎么流转。
- **组成轴** `interaction-spec/surface-model.md` 的「布局骨架（机器段）」区域树——页面怎么排；page_state 里每个可见对象用 `region` 落到一个区域。

原型按这两轴实现，`harness interaction project` 由行为图派生三视图 + 演示导览播放器数据 `walkthrough.js`。

## 九条设计要求（R1–R9，每条可检验）

### R1 按 surface 切页、按 page-state 切块
- 一个 surface = 一个页面（`board.html` / `frame.html` / `index.html` …）；应用级独立面各自成页。
- 一个 page-state = 页面内的 `data-state` 态块，默认显示主态。
- **叠加面（抽屉 / 弹窗 / 浮层）作 overlay 承载在宿主页里**，不独立成页；它有自己的 surface id，`page_entry` 指向宿主页 `#hash`。
- **页面数追随 surface 数，不随 state 数膨胀**——禁止"一个状态一个文件"。
- 检验：页面数 ≤ surface 数；每个 `page_state.surf` 落在 surface-model 的 surface 目录里。

### R2 每个 page-state 可寻址、带静态锚点
- 态容器写 `data-pagestate="PS-<surf>-<state>"`；触发该拍的控件 / 容器写 `data-step="SUC-x-FLOW-y.<state>"`。
- 即使默认隐藏，锚点也内联在静态 HTML 源码里（lint 扫 HTML、人读得到全貌）。
- 检验：四方锚点对账 `behavior-graph.steps↔data-step`、`page_states↔data-pagestate`。

### R3 每条 edge 是真实产品操作
- 用户动作 edge = 真控件（点 node、进对话、切 tab）。
- 系统事件 edge = **产品输入诱发**（切 workspace、选数据源 → 自然得到不同结局），声明 `edge.via=<surf>/<控件名>`，原型提供带 `data-via` 的真实控件。
- **禁止 dev 状态开关条 / 调试按钮**直接翻状态。判定线：操作的是产品数据/上下文（✅）还是状态本身（❌）。
- 检验：每条 system_event 有 `via` 且在 surface 的 via 控件清单 + 原型 `data-via` 元素。

### R4 每个 page-state 都有真实操作可达路径
- 从 surface 入口出发，必须存在一条由**真实产品操作（edge）**组成的路径到达每一个 page-state；**不存在"产品里没有任何操作能走到、只能靠 hash 到达"的态**（hash 是演示导览的驱动手段，不是产品到达路径）。
- 典型坑：定义了 no_slice / stale 等态，但入口页没有指向它们的操作 → 产品里走不到。修法是补齐入口 surface 的触发点 / `edge.via` 控件，而不是只靠 hash。
- 检验：`harness interaction prototype-check` 的图可达性（`PAGESTATE_UNREACHABLE`，**默认 FAIL**，可经 `interaction.reachability_gate_level=warn` 临时降级（不建议））——纯静态分析，不靠人肉走查。

### R5 内容静态、JS 只做胶水 + page-state 可 hash 激活
- 所有 surface 与态都是**预写好的静态 HTML 块**；JS 只负责：按产品操作切态块可见性、局部 mutation、跨页导航、toast。
- **page-state 必须可由 `location.hash = '#' + pageStateId` 激活**：原型监听 `hashchange`（及首屏 hash），把对应 `[data-pagestate]` 块设为激活（如加 `[data-active]` 并显示）。这是演示导览播放器逐拍驱动原型的统一契约，让播放器与具体原型解耦。
- 保证任一时刻有且仅一个激活的 `data-pagestate`（激活块带 `[data-active]` 或唯一可见）。
- **禁止用 JS 从 fixture 渲染业务内容**（`createElement` / 拼 DOM）——否则静态文件看不到全貌、锚点埋进 JS 扫不到。
- 检验：无 createElement 渲染业务内容；`#<page_state>` 能激活对应态块。

### R6 文案中文、人确认、长期工程
- 用户可见文案默认中文；品牌名、枚举值 / 程序标识（`permission_mode`、模型 id 等）、领域字段键可保留英文。
- 主原型写入独立原型工程目录（`prototype.interactive_prototype.prototype_project_root`，默认 `prototype/`），随 Mission 分支隔离、长期迭代，不在 `project-knowledge/` 或 mission artifact 下另起副本。
- **先写设计意图，再写像素**：动 HTML 前先在 `interaction.md` 写「设计意图」一节——视觉方向 / 气质（引 `design-system/principles.md` 气质坐标）、每个关键 surface 的主角与强调（区域树是骨架槽位 ≠ 视觉层级，必须显式说强调谁）、关键 `OBJ-xx` 的真实内容样例（非 lorem）、参考与非目标。无来源时主动问用户，不静默自行发明。它是 designer 的靶子、reviewer 表达对照的依据、用户确认时一并查看的方向说明（偏差高发口）。
- **设计意图与像素之间隔一层低保真 ASCII 线框**：写完设计意图、动高保真 HTML 之前，先把步骤区域树渲染成一张**低保真 ASCII 线框**（每个关键 surface 一张，用 ASCII 框线画区域块 + 中文占位标签，按区域树的嵌套与扫描序排）。它是区域树的人类可读渲染——**出具极快、人扫一眼即可核对组成、AI 直接读文本、且物理上无法精修**。`compose-before-HTML` 因此字面成立：ASCII 在前定组成，HTML 在后上像素，比例 / 密度 / 视觉权重留给高保真，"低保真滑向高保真 lite"的精修化风险被介质本身切断。结构正确性仍由区域树 + R8 组成门程序化兜底，ASCII 只是它给人看的派生视图——三级链路 `区域树(机器真相) → ASCII 线框(人扫一眼) → 高保真 HTML(像素)`，职责不重叠。线框存 `visual-interaction/variants/**`（纯文本，如 `lowfi-wireframes.md`），占位标签同样默认中文。
- **用户确认默认走 harness 框架方式**：交互 Gate 要求用户确认原型表达符合预期，**默认入口是演示导览播放器 `harness-prototype-frame.html`**（逐拍驱动真实原型 + 旁白带验收点），而不是把人丢到裸 `index.html` 自己乱点；裸可操作原型作为播放器 iframe 驱动对象保留并提供自由操作二级入口。确认时连同「设计意图」与低保真 ASCII 线框一起呈现，便于核对方向（`harness approval append --type checkpoint --stage interaction --status approved`）。

### R7 导航 3 层封顶、结构干净
- 演示导览播放器左栏只 **SUC → flow → step** 三层；step 在 flow 下是有序列表，不再嵌套。
- 顶部只「本任务 / 项目已有」两组；OP / 组件 / BO 不作导航节点（作为信息 chip 或在态块内呈现）。
- 检验：导航树深度 ≤3、无第 4 层。

### R8 页面按布局骨架组成、对象落区、HTML 打 data-region（组成轴）
- **先有骨架再有像素**：每个有 page-state 的 surface 必须在 surface-model「布局骨架（机器段）」声明一棵区域树（区域 × 嵌套 × 排布 × 优先级 × 角色 × 扫描序）；缺 → `LAYOUT_REGION_MISSING`（FAIL）。
- **可见对象必落区**：`behavior-graph.yaml` 里每个可见对象（`objects[].fields` 非空）必须用 `region` 落到区域树里的某个区域；非 OBJ 内容（动作 / 空态 CTA / 状态）用 `placements` 落区。对象无 `region` = 控件无家可归 = 乱堆 → `OBJECT_UNPLACED`（FAIL）。
- **区域属于本 surface**：对象 / placement 的 `region` 必须命中**本 page_state 所属 surface** 的区域（区域「所属 surface」== page_state.surf），否则 `OBJECT_REGION_UNKNOWN` / `REGION_SURF_MISMATCH`（FAIL）。
- **原型忠实渲染骨架**：原型 HTML 为每个承载内容的区域打 `data-region="<区域 id>"`；声明承载却没渲染 → `REGION_NOT_RENDERED`（FAIL，与 R2 四方锚点同构）；HTML 出现骨架里没有的区域 → `REGION_ANCHOR_DANGLING`（FAIL）。
- **声明扫描动线**：同父区域用 `扫描序` 编码阅读顺序，缺 → `SCAN_ORDER_MISSING`（WARN）；声明了却全程不承载任何内容的区域 → `REGION_DEAD`（WARN）。
- **从 pattern 起，不从白纸起**：新建 surface 选 `references/layout-patterns/` 里匹配的布局 pattern 作基底骨架再裁剪。
- **基线优先（迭代系统）**：改 / 扩既有 surface 必须继承项目级累积图 `regions` 里既有区域树（及既有原型 `data-region` 结构），只写增量；既有区域被回归校验（合并图里仍须渲染），删除走顶层 `retired:`。贴合项目设计系统基线 `project-knowledge/product/ui-design-system.md`（token / 组件原语 / 布局与交互约定），保证本次原型与既有界面一致、下游实现无歧义。
- 检验：`harness interaction prototype-check` 的 `composition` 类 finding（对账合并图：项目级累积 ∪ 本 mission）。
- **门的边界（诚实声明）**：组成门保证「对象都有家、骨架被忠实渲染、有阅读顺序」，它**判定不了审美 / 精致度**。精致度靠 compose-before-HTML 的低保真 ASCII 线框人评 + interaction-reviewer 组成 lens + pattern 库地板，三者合起来才治"第一版乱堆"。

### R9 从设计系统组件库装配（不堆裸控件）
- **从组件库装配**：原型不从裸 HTML 一控件一控件堆，而是挂在设计系统的应用外壳里（`data-shell="SHELL-…"`）、区域里渲染**业务组件实例**（`data-bizcomp="UC-…"`，引 `ui-design-system` 的 `design-system/business-components.md`）、业务组件由基础组件搭、全用 `prototype/tokens.css` 的登记 token。设计系统 = 设计原则 + 整体交互框架 + 基础组件 + 业务组件 + 设计规范（见 `project-knowledge/product/ui-design-system.md`）。
- **业务组件可追溯**：每个业务组件绑上游 `SUC-xx`/`OBJ-xx`（traces_to 不悬空）、声明由哪些基础组件（`BC-*`）组成、列全状态矩阵；可见对象可用 `behavior-graph` 的 `objects[].bizcomp` 标明由哪个业务组件渲染。
- **原型锚点对账**：原型 `data-bizcomp` / `data-shell` 必须命中设计系统目录，否则 dangling；业务组件 `组成` 的 `BC-*` 必须在基础组件目录。
- **迭代继承、增量沉淀**：改 / 扩既有 surface 复用既有业务 / 基础组件、不重造；本次新定义的业务组件沉淀进 `business-components.md` + 实现于 `prototype/components/business/`。
- 检验：`harness interaction prototype-check` 的 `design_system` 类 finding（**warn 滚动**：新增门按 warn 提示，项目采用组件库后由 `interaction.design_system_gate_level=fail` 升级强制；**非破坏边界**：组件库目录为空 = 未采用 = 门不触发）。

## 演示导览播放器（显示与引导）

`harness-prototype-frame.html` 是 dev-only 演示导览播放器（非 operable 产品入口），读 `walkthrough.js`（`window.__HARNESS_WALKTHROUGH__`，由 `harness interaction project` 生成）。它的定位是**引导式演示 / 产品导览**，不是"让人做走查任务"：

- **左栏**：SUC → flow（演示场景）→ step（拍）三层；点 flow 从头导览，点具体拍直接跳到该拍。
- **中间**：iframe 内嵌真实主原型，由播放器**自动驱动**（导航到 `page_entry` + 用 `#<page_state>` 激活该态）。
- **底部演示控制条 + 旁白**：「◀ 上一步 / 下一步 ▶ / ▶ 自动播放 / ↻ 重播」+ 进度点；旁白讲解当前拍的触发（`edge.desc`/`edge.via`）、看到的态、验收点（`acceptance_refs`）。
- 用户只需点「下一步 / 自动播放」观看，**不需要自己操作**——这是演示/引导。

> **可达性 / 覆盖的验证不靠人肉走查**：每个 page-state 是否能被真实操作到达（R4）、是否被锚点覆盖，全部由 `harness interaction prototype-check`（静态 reachability + coverage）保证。播放器面向"人确认原型表达是否符合预期"，用 hash 逐拍驱动是演示手段，不构成对 R4 的违反——R4 是图层面的静态保证。

## 本地预览服务端口（多项目共存，强制）

无论 `interactive_prototype`（静态原型 + 播放器）还是 `frontend_engineering`（`pnpm dev`），当你为用户起任何本地预览 / 静态 / dev server 时，必须遵守：

- **先探测端口**：起服务前先检查目标端口是否被占用（如 `lsof -i :<port>`）。
- **被占用就换空闲端口**：dev server 用 `--port <free>` 显式指定，或允许其自动递增；静态服务（如 `python3 -m http.server <free>`）直接选未占用端口。
- **绝不停掉已在跑的服务**：禁止 `kill` / `fuser -k` / 任何停止占用端口进程的动作——本机可能并行运行用户其它项目的原型服务，停掉会破坏对方。
- **告知实际地址**：启动后把真正使用的端口 / URL 明确告诉用户；多项目并存时各服务用各自独立端口，互不干扰。

## 跨 Mission 累积：两层行为图（关键）

原型是**项目级长期工程**，承载所有 Mission 累积的 SUC；而 mission 的 behavior-graph 只是本次**增量**。两者分两层：

- **项目级累积图**（SSOT，"长期原型任何时刻必须承载什么"）= `project-knowledge/product/system-use-cases/behavior-graph.yaml`，是所有已关闭 Mission 图的并集。它内联 `surfaces:` 目录（surface catalog）与 `regions:`（**布局骨架 / 区域树**），不依赖某个 mission 的 surface-model —— **行为基线与组成基线住在同一份累积图**。
- **mission-local 增量图** = `interaction-spec/behavior-graph.yaml`，本次新增 SUC + 对既有的 modify/extend、显式 `retired: [page_state/step/region ids]` 删除，以及 `superseded:`（**迭代取代**，见下「四招」）。
- **设计系统**（视觉 / 交互语言 + 组件库）= `project-knowledge/product/ui-design-system.md`（索引）+ `design-system/`（设计原则 / 整体交互框架 / 基础组件 / 业务组件 / 设计规范），真实可消费物在原型工程 `prototype/tokens.css` + `prototype/components/`，外加组件库可视化展示页 `prototype/component-library.html`（按组件 × 全状态矩阵陈列供人对账——**是参考展示页、不是 SUC 原型**，按组件分区陈列是其本职，不受 R4「原型不许 gallery 堆叠」约束）。**原型从这套系统装配**：surface 挂应用外壳（`data-shell`）、区域里放业务组件（`data-bizcomp`，绑 OBJ/SUC、由基础组件组成）、组件用登记 token，不从裸控件堆；迭代继承既有外壳 / 区域 / 组件与设计语言。retrospective 增量沉淀业务组件 / 基础组件 / token / 约定（不整份覆盖）。
  > 注：R8（组成门 `composition`）管布局骨架 + 对象落区；R9（设计系统门 `design_system`）管从组件库装配——两门均 warn 滚动、采用后升 fail。登记 token 的散落魔法值校验暂未做（需解析 CSS，易误报），先靠 reviewer 把关。

**迭代一个既有 surface 的四招（关键——别再被逼到"两个看板并存"）**。新 mission 碰到一个项目级沉淀的 surface/锚点时，有且只有四种合法动作，按"身份是否延续"+"覆盖是否延续"选：

| 动作 | 何时用 | id | 覆盖 | 机制 |
|------|--------|----|----|------|
| **keep**（默认不动） | 沉淀面本次不涉及 | 沿用 | 沿用 | 回归门要求它仍被锚定 |
| **modify / extend** | 同一 surface 原地演进、语义连续 | **沿用同一批 id** | 沿用 + 增量 | mission 图用同 id 覆盖项目图行 |
| **supersede（取代承接）** | 沉淀面被**换代**成一个改了名 / 换了结构的后继（lane×node 看板 → mission×stage 看板；同一真实组件进化），语义变到不宜复用旧 id | 旧 id → 新后继 id（`anchor_map` 记对应） | **由后继承接** | `superseded:` 把前驱锚点从合并图丢弃（不再要求物理在册，原型只剩一个面），但**强制后继真实存在 + 被覆盖** |
| **retire（删除）** | 沉淀能力本次真的废弃、无后继 | 旧 id 移除 | **丢弃** | 顶层 `retired: [ids]` |

> `supersede` 是 `retire` 的"带承接者"版本——比 retire 信息更全（说清覆盖去了哪），比 keep 干净（不留并存）。**当一个新版本是对旧版本的迭代、且涉及旧锚点升级时，走 supersede，不要 keep（会撞出两个面）也不要 retire（会丢血缘）。**

`superseded:` 形态（mission-local `behavior-graph.yaml` 顶层，与 `retired:` 并列）：
```yaml
superseded:
  - predecessor: SURF-BOARD          # surface | suc | page_state | step
    successor:   SURF-CP-BOARD        # 必填：承接覆盖的后继（本 mission 增量）
    kind: surface
    anchor_map: {PS-SURF-BOARD-readable: PS-CP-BOARD-ready}   # 可选：能对上的逐个映射（血缘）
    dropped: []                       # 显式承认未承接的覆盖（非空须 reviewer bless）
    rationale: "lane×node 工作图看板进化为 mission×stage 控制面看板（同一 WorkGraphBoard.tsx 扩展）"
```

**`harness interaction prototype-check` 对账的是 (项目级 ∪ 本 mission) 合并图**（whole-prototype 回归门）：
- 本 mission 增量：必须锚定 + 覆盖（问责本次）。
- 项目级沉淀：**回归校验**——必须仍被锚定，除非本 mission 显式 `retired`（删除）或 `superseded`（取代承接）。这样新 mission 改原型不会悄悄退化掉旧 SUC。
- **supersede 防退化后门**：被 `superseded` 的前驱，其后继必须真实存在于合并图（本 mission 增量）并被覆盖，否则 `SUPERSEDE_SUCCESSOR_MISSING`（FAIL）——杜绝"假取代真删除"。`dropped` 非空或缺 `rationale` 报 WARN，由 interaction-reviewer 判是否退化。
- dangling = 锚点在合并图里都找不到才算漂移（沉淀锚点合法，不再误报）。

**`harness interaction project`** 从合并图派生视图与 `walkthrough.js`，并把本 mission 的 SUC 打 `focus=true`；演示导览播放器据此分「**本任务**」/「**项目已有**」两组——评审既走本次新 flow，也能用演示回归老 flow 仍可达。

- **设计期纳入**：designer 设计前必读项目级累积图（含 `surfaces` + `regions` 区域树）+ SUC 注册表 + 设计系统基线 `ui-design-system.md` + 既有原型的 `data-region` 结构；长期原型已承载这些 SUC 与布局，本次只做**增量增改、不破坏**（删除须显式 retire），新区域贴合既有设计语言。
- **关闭期沉淀**：Mission 关闭走 `harness knowledge promote` 时，mission 图**并入**项目级累积图（新增/改/retire/**supersede**）；supersede 会从累积图移除前驱、由后继承接，并在 `superseded_log` 留 `predecessor → successor` 血缘，供后续 mission 追溯。SUC 注册表为其派生视图。

## 推荐文件结构

```
prototype/
  index.html                 # 主 surface 页 = 可操作原型本体（播放器 iframe 驱动对象 + 自由操作二级入口）
  <surf>.html                # 每个 surface 一页（board.html / frame.html …）
  assets/
    styles.css               # 共享样式基座（间距/字阶/色彩角色 token）+ 区域树布局规则 + data-state 切换可见性
    proto.js                 # 交互胶水（切换/导航/toast/局部 mutation + 暴露 data-active），不渲染内容
  harness-prototype-frame.html  # dev 演示导览播放器（模板渲染，勿手改逻辑）= 用户确认默认入口
  walkthrough.js             # 由 harness interaction project 生成（演示导览播放器数据源）
```

## 与对账命令的关系

- `harness interaction prototype-check --prototype-root prototype`：**唯一 lint**，一次对账返回 `{status, findings[]}`，findings 按 category 分（graph / reachability / anchor / coverage / locator / upstream）。
- `harness interaction project --prototype-root prototype`：从 behavior-graph 派生 `views/by-suc|by-surface|by-object.md` + `walkthrough.js`。
- viewport 覆盖仍来自 `harness evidence visual manifest` 生成的 manifest（behavior-graph 不含视口轴）。

## lint 的覆盖宇宙（PASS 才真代表全覆盖）

PASS 必须意味着"项目所有 SUC / flow / 节拍都进了图、且被原型体现"。为此 prototype-check 把**全链都做成 FAIL 级门**，不能只验图→原型：

| 链路 | 门 | finding |
|------|----|---------|
| **PRD use-case-model → 图** | 每个 `SUC-NN` / 流步骤 `SUC-NN-FLOW-NN` / 节拍 `SUC-NN-FLOW-NN.<state>` 必须在（合并）图里 | `UPSTREAM_SUC_NOT_IN_GRAPH` / `UPSTREAM_FLOWSTEP_NOT_IN_GRAPH` / `UPSTREAM_BEAT_NOT_IN_GRAPH`（FAIL；非界面承载的节点一律走 `surface-model.md` 的「N/A 豁免（机器段）」结构化表豁免，不再在散文里写 `N/A`/不适用 + SUC token；豁免声明了但节点其实已落图报 `NA_EXEMPTION_STALE`(FAIL)） |
| **项目级 SUC 注册表 → 项目图** | 每个项目级注册表 SUC（前缀无关，从 `project-knowledge/product/system-use-cases/*.md` glob 抽取）必须在项目级累积图有 flow | `UPSTREAM_REGISTRY_SUC_NOT_IN_GRAPH`（FAIL） |
| **PRD 扇出结局 token 完整性** | 流步骤一旦在 use-case-model 用「扇出」描述多结局，必须为该流步骤建 ≥1 个 `SUC-NN-FLOW-NN.<state>` 节拍 token，否则散文结局静默漏出对账分母 | `PRD_FANOUT_BEATS_MISSING`（FAIL） |
| **图 → 原型** | 每个 step/page_state 有锚点、可达、flow 边可操作、via/testid 齐 | graph/reachability/anchor/coverage/locator 类（FAIL） |
| **骨架 → 原型（组成轴）** | 每个 surface 有区域树、每个可见对象落区、原型区域忠实渲染、有扫描序 | `composition` 类（`LAYOUT_REGION_MISSING` / `OBJECT_UNPLACED` / `OBJECT_REGION_UNKNOWN` / `REGION_NOT_RENDERED` / `REGION_ANCHOR_DANGLING` FAIL；`SCAN_ORDER_MISSING` / `REGION_DEAD` WARN） |
| **设计系统 → 原型（组件库）** | 从组件库装配：业务组件绑 OBJ/SUC + 组成 BC 存在、原型 `data-bizcomp`/`data-shell` 不 dangling、对象经业务组件承载 | `design_system` 类（`BIZCOMP_BASE_UNRESOLVED` / `BIZCOMP_BINDING_DANGLING` / `OBJECT_BIZCOMP_UNKNOWN` / `BIZCOMP_ANCHOR_DANGLING` / `SHELL_ANCHOR_DANGLING` 按门级；`OBJECT_NO_BIZCOMP` / `BIZCOMP_STATE_MISSING` WARN）；warn 滚动、空目录不触发 |

> 没有 upstream 完整性门时，把某 SUC/flow 从图里漏掉会**静默 PASS**（图自身不全，但图→原型对账通过）。补上后，PASS = 上游清单 → 图 → 原型 全链气密。

## 反模式清单（评审必查）

- ❌ 一个状态一个 HTML 文件（应 state 是页面内的块）。
- ❌ 一页把某 SUC 所有状态并排堆叠成 gallery（应默认主态 + 正常操作切换，一次一态）。
- ❌ JS 从 fixture 渲染业务内容（应静态 HTML + 交互胶水）。
- ❌ 用 dev 开关条 / 调试按钮切状态（应产品输入诱发，声明 `edge.via`）。
- ❌ trace 锚点只存在于 JS 字符串里（应内联静态元素）。
- ❌ page-state 不支持 `#<page_state>` hash 激活（演示导览播放器无法逐拍驱动）。
- ❌ page-state 只能 hash 到达、产品里没有任何真实操作能走到它（违反 R4，prototype-check 报 `PAGESTATE_UNREACHABLE`，**默认 FAIL**；仅可经 `interaction.reachability_gate_level=warn` 临时降级，不建议）——hash 是演示手段，但每个态仍必须在产品里有真实操作路径。
- ❌ 导航树铺 OP / 组件 / BO（应只到 SUC→flow→step 三层）。
- ❌ **没有布局骨架就直接写 HTML**，控件随意堆（违反 R8，surface 缺区域树 `LAYOUT_REGION_MISSING`）。
- ❌ **可见对象不落区**（应在 `objects[].region` 落到声明区域，否则 `OBJECT_UNPLACED`）。
- ❌ **整页一坨**：所有对象塞进一个无区分的容器（应按区域树的主次 / 角色 / 扫描序分区组织）。
- ❌ **原型区域与骨架对不上**：HTML 区域 `data-region` 与布局骨架不一致（`REGION_NOT_RENDERED` / `REGION_ANCHOR_DANGLING`）。
- ❌ **跳过 compose-before-HTML**：第一版直接出高保真 HTML 而不先出低保真 ASCII 线框给人评组成。
- ❌ **绕过组件库自由发挥**（R9）：项目已有业务组件库，却在原型里另堆一套裸控件、不复用 / 不沉淀业务组件。
- ❌ **业务组件悬空**：业务组件不绑上游 SUC/OBJ、或组成的 BC 不在基础组件目录、或原型 `data-bizcomp` 在目录里查无此组件。
