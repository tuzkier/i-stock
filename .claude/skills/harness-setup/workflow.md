# Harness Setup 工作流

**Goal:** 在 `install.py` scaffold 之后，把项目编排成"可用的 Harness 项目"——或对已安装项目做 re-init / 把更新类操作导到权限化命令。

**Your Role:** 你是安装编排者。你不重复 `install.py` 的拷贝工作，也不手改框架正文去"更新"；你判断模式、按序跑初始化与建图、调用对应子技能 / 命令、验证并移交。所有 CLI 经 `harness-cli`（`--json`）。

**关键原则：**
- 只新增、不覆盖已有 runtime 数据与项目知识。
- 失败不静默跳过：记录原因 + 给补救动作，再决定继续或停。
- 既有项目建图走 `graphify-build` 技能（免 Key），不裸跑 `graphify .` 建文档图。

---

## 初始化

1. 确定项目根 `TARGET`（当前工作目录或用户指定；不明确先问）。
2. 检查 `TARGET/harness-runtime/bin/harness` 是否存在（**harness CLI 是「是否已安装」的判据**——后续一切操作都经它，CLI 不在说明还没 scaffold，回 INSTALL.md 先跑 clone + `install.py`，不在本技能里 scaffold）。
3. CLI 就位后，调用 `harness-cli` 执行 `harness config snapshot --json`，确认控制面就位、读取 `brownfield` / `project_name` / `default_mode`；不要直接读 `harness.yaml`。

> Windows（PowerShell）：所有 `harness-runtime/bin/harness <args>` 改成 `python harness-runtime\bin\harness <args>`。

---

## 执行

<workflow skill="harness-setup" version="1">

<step n="0" goal="判模式">
  按下表定模式，再跳到对应步骤：

  | 信号 | 模式 | 去 |
  |---|---|---|
  | CLI 就位（`harness-runtime/bin/harness`）+ 无 `project-context.md` | `install` | Step 1 |
  | CLI 就位 + 有 `project-context.md`，但 Step 4 验证有缺项 | `re-init` | Step 1（只补缺项） |
  | 用户要升级到新版本模板（框架正文 / runtime 结构 / yaml 任意一项） | `upgrade` | Step 6 |
  | 用户要追加 AI 工具入口 | `add-adapter` | Step 6 |

  - `re-init` 只补跑缺失项，已完成的步骤跳过；绝不重跑会覆盖数据的命令（如 `knowledge init`）。
</step>

<step n="1" goal="初始化控制面（install / re-init）">
  在 `TARGET` 内：

  - `harness context init --json` —— 生成 `project-context.md` 骨架（已存在则跳过，不覆盖）。成功判据：`status: PASS` 且文件存在。
  - `harness knowledge check --json` —— 只校验，**不要 `knowledge init`**（scaffold 已铺好，再 init 会 FAIL）。成功判据：`status: PASS`。
  - 设 `project_name`：从 `harness config snapshot` 看是否为空（`''`）。为空时取 `TARGET` 目录名作为默认值，或问用户确认，再写入（无 config 写命令，直接改该行）：
    ```bash
    sed -i.bak "s/^project_name: .*/project_name: '<项目名>'/" harness-runtime/config/harness.yaml && rm -f harness-runtime/config/harness.yaml.bak
    ```
  - 确认 `brownfield`：**默认 true，既有项目不动**。仅当项目确属全新 / 空（无 git 历史、无任何源码 / 文档 / 配置内容）才覆盖为 false：
    ```bash
    sed -i.bak 's/^brownfield: .*/brownfield: false/' harness-runtime/config/harness.yaml && rm -f harness-runtime/config/harness.yaml.bak
    ```
    > 既有项目判定本质是"是不是已有内容的存在项目"，不是"有没有某几种源码后缀"；纯文档 / Markdown 项目也是既有项目。拿不准按既有项目。
  - 改完 `harness config snapshot --json` 确认 `project_name` / `brownfield` 为预期值。
  - 其余重型特性开关（`spec` / `agent_engineering` / `e2e` / `project_lint`）保持模板默认（全开），安装不裁剪；用户后续按需自行调 config。
  - **写 Harness 本地产物 `.gitignore`（install / re-init 都跑，绿地棕地都跑）**：框架 / adapter / runtime 结构与项目知识入 git 团队共享，但 **harness CLI / graphify 在本项目跑起来后才生成的本地产物 / 缓存 / 字节码不入 git**。幂等追加（已有行跳过）：
    ```bash
    for L in \
      '__pycache__/' \
      '*.pyc' \
      '*.pyo' \
      '.pytest_cache/' \
      '.worktrees/' \
      'harness-runtime/harness/state/transactions/' \
      'harness-runtime/harness/traces/**/backup/' \
      'harness-runtime/harness/traces/**/staging/' \
      '*.bak' \
      '*.bak[0-9]*' \
      '**/skills/**/config.json' \
      'harness-runtime/harness/artifacts/**/setup/design-system-staging/'; do
      grep -qxF "$L" .gitignore 2>/dev/null || echo "$L" >> .gitignore
    done
    ```
    > 逐条理由：`__pycache__/` `*.pyc` `*.pyo` = harness CLI 与 graphify 的 Python 字节码（scaffold 不拷，运行时才生成）；`.pytest_cache/` = 跑 harness / 项目测试的缓存；`.worktrees/` = git-workflow 建的 stage worktree；`state/transactions/` 与 `traces/**/{backup,staging}/` = 控制面事务日志与 trace 备份 / 暂存（本地运行数据，非可复审产物）；`*.bak` `*.bak[0-9]*` = **升级（harness-upgrade）原地写 config 时自动生成的 `harness.yaml.bak` 等备份文件**——属升级本地回滚点，不入 git；`**/skills/**/config.json` = 各 adapter 技能含密钥的本地 config。`graphify-out/` 的本地缓存在 Step 2（仅既有项目建图后）追加，不在此。`.DS_Store` 等 OS 噪声属项目自身约定，按需自加，不进 Harness 块。
</step>

<step n="2" goal="既有项目：建图（graphify-build）→ 填充上下文（generate-context）；全新项目跳过建图">
  职责分清：**建图 = `graphify-build` 技能**；**填 `project-context.md` = `generate-context` 技能**（它需要图谱，但图谱已建好就直接复用，不重建）。harness-setup 不自写建图逻辑，建图单一出处是 `graphify-build`。

  - **全新项目**（`brownfield: false`）：不建图；`project-context.md` 骨架先留空，AI 在第一个任务执行后再询问用户补全。本步到此。
  - **既有项目**，按序：
    1. **确保 graphify 运行依赖**：`harness graphify status --json` 看 `cli_installed`；为 `false` 则机器级装一次 `uv tool install graphifyy`（PyPI 包名双 y）。`graphify-build` 内部 import graphify 做代码 AST 抽取，必须有这个包；构建技能本身已随 Harness 安装，**不要再 `graphify install`**。
    2. **建图：调用 `graphify-build` 技能**（代码 AST + 文档由你当前会话派发子 agent 提取，**全程免 Key**）。**现在就建，别甩给用户，别裸跑 `graphify .` 建文档图。**
       - **语义分析不准跳过**：文档 / Markdown / PDF / 图片的语义抽取是建图的一部分，不允许只做代码 AST 就收工。
       - **代码 AST 走 CLI 机械抽取**（`graphify extract`，确定性、快、免 LLM、不派子 agent）——超大型项目主体是代码，这部分规模无关，先跑。**只有非代码 + 未缓存的文档/MD/PDF/图片才派子 agent 做语义提取**。
       - **扇出按计算出来的计划执行，不靠"感觉量大就多 spawn"**：把未缓存非代码文件清单交给 partition planner 算分区 / 批次 / 波次 / reduce 计划，再照计划 dispatch：
         ```bash
         # uncached.txt = graphify 检测出的未缓存非代码文件清单（每行一个路径）
         python3 .harness/common/skills/harness-setup/scripts/partition_plan.py \
           --files-from uncached.txt --chunk 22 --concurrency 10 --threshold 150 --json
         ```
         - `mode=simple`（< threshold）→ 现状：按 `ceil(N/22)` 平铺派子 agent，一波或两波即可。
         - `mode=partitioned`（≥ threshold，超大型）→ **按 `partitions` 派子 agent，每个子 agent 只看一个模块的一批文件**（局部性好、跨文件语义边更准、上下文不爆）；**按 `waves` 一波一波 dispatch**（尊重并发上限，不假装无限并行）；按 `priority_rank` 先扫高价值模块。
         - reduce：graphify 的 Part C 合并是**机械 Python 去重**（按 id），规模无关，照常合并即可——这里不需要分层 reduce（分层 reduce 是蒸馏 Step 3 才需要的）。
         - **不得因量大而跳过或截断语义抽取**：计划覆盖全部未缓存非代码文件；缓存（`graphify-out/cache/`）让重建只碰改动文件，成本被增量摊销。
       - 建完 `harness graphify status --json` 期望 `available: true`、`indexed: true`。
    3. **追加 graphify `.gitignore`**（在 Step 1 的 Harness 本地产物块之上补 graphify 专项）：图谱本体（`graph.json` / `GRAPH_REPORT.md` / `graph.html`）入 git，其余本地 / 派生产物忽略：
       ```bash
       for L in 'graphify-out/cache/' 'graphify-out/manifest.json' 'graphify-out/cost.json'; do
         grep -qxF "$L" .gitignore 2>/dev/null || echo "$L" >> .gitignore
       done
       ```
    4. **填充上下文：调用 `generate-context` 技能**——图谱已建好，它直接复用（不重建），扫描代码结构 + 图谱填 `project-context.md`，并生成 / 更新 project-lint；顺带采集 UI 设计语言信号（CSS 变量 / token 文件 / theme / 组件库 / `materials/design/`），供下一步 Step 3 蒸馏。
</step>

<step n="3" goal="蒸馏 UI 设计系统初版（既有项目 UI；放在 graphify + generate-context 之后）">
  仅 **既有项目** 执行；全新项目（Step 2 已整步跳过）跳过本步。**放在 graphify 建图 + generate-context 之后**，因为蒸馏要靠图谱 + 上下文定位 token / theme / 组件，而不是盲扫。

  - **是否蒸馏只认 generate-context 的 `ui_presence` 机械判定 + 命中证据，主 agent 不得用主观印象覆盖**：先读 generate-context 输出的 `ui_presence` 值与**命中信号证据清单**（哪些信号命中：React/Vue/TS 组件、`package.json` UI 依赖、jQuery、`.cshtml`/`.razor`/模板、CSS/SCSS、`wwwroot/css`、`prototype/`、图片资产等）。这是 Step 3 的唯一判据——**严禁主 agent 凭"这看着是个后端项目 / 主要是 .NET / 主要是后端 API"之类主观二分盖过机械结果**。
    - `confirmed_ui`（命中任一信号）→ **必须蒸馏，不存在跳过选项**。哪怕前端是 jQuery + 服务端模板这类"不时髦"的栈、哪怕没有任何设计 token / 设计系统，只要有界面就从**真实渲染的组件**观察蒸馏；抽不到 token 标「待补」+ 留 init 占位，**整步跳过不合法**。
    - `no_signal`（零信号命中）→ **不得静默跳过**。向用户确认「未检测到界面信号，这是 UI 项目吗？」，**默认按"有 UI"推**；用户确认无界面（纯后端 / CLI / 库）才跳过并在收尾报告记录原因；用户确认有界面，则请其指明界面所在（如 `.cshtml` / `.xaml` / 模板目录）后再蒸馏，无可抽真值时留 init 占位 + 标「待补」。
    - **概念去偷换（高频踩点）**：「无设计系统 / 无设计 token」≠「非 UI 项目」≠「可跳过」。有 UI 信号 = UI 项目 = 必须蒸馏（从真实组件观察），缺 token 只是标「待补」，**不是跳过整步的理由**。把"无现有设计系统"当成"跳过此步"的借口、或在验证 / 收尾里写"非 UI 项目正常"而 `ui_presence=confirmed_ui`，都是违规静默跳过。
    - **跳过必须留证据**：任何跳过（仅 `no_signal` + 用户确认无界面这一条合法路径）必须在收尾报告记录 `ui_presence` 值、命中证据为空的事实、用户确认原文。`confirmed_ui` 没有合法跳过路径。

  > ❌ 反模式（这正是过去翻车的原话，命中即违规）："本项目主要是 .NET 后端 + jQuery 前端，无现有设计系统，跳过此步"、"设计系统文件未索引（非 UI 项目正常）"。只要 `ui_presence=confirmed_ui`（jQuery 前端、`package.json`、CSS、`.cshtml`、`prototype/`、图片资产任一命中即是），这两句都是错的——必须蒸馏。

  - **蒸馏前先确认既有设计资产 + 取目录（让蒸馏精准、并把既有标准吸纳进 Harness 格式）**：`confirmed_ui` 确认后、动手扫描前，**先问用户**：本项目是否已有一套**现成的设计系统 / 组件库 + 主题定制**（如 Element UI / antd / MUI + 自定义主题，或团队自有组件库 + 设计规范）？读 generate-context 的「既有组件库 / 设计系统底座识别」信号作为已知线索一并呈现。
    - **有 → 请用户指明位置（不靠盲扫猜）**：用的是哪个组件库（及载体：npm 包 / 仓库内 vendored）、主题 / 变量定制文件在哪（如 `element-variables.scss` / `theme/*.ts` / 全局 CSS 变量）、项目自研 / 二次封装组件目录、设计规范文档（或放进 `materials/design/`）。蒸馏**优先吸纳这些指定位置**，按下方各子 agent 的「来源归属分流」处理。
    - **无 / 用户不确定 → fall back 机械扫描**：按 generate-context 命中证据 + partition planner 扫 UI 根，从真实渲染观察蒸馏。
    - **为什么仍要蒸馏、不是"直接用就完了"**：项目既有标准的形态（散落的 SCSS 变量 / 第三方库默认 + 局部 override / 无结构的组件目录）**不一定符合 Harness 下游要求的格式**（design-system 各层 + 全状态矩阵 + 绑 OBJ/SUC 的业务组件 + 区域树）。蒸馏 = 把既有标准**吸纳 / 规范化进 Harness 格式**让 interaction / 原型 / 治理门能消费；**组件本体仍直接用既有库、不重画**，吸纳的是"用了哪个库（载体）+ 项目主题定制真值 + 自研 / 封装 / 业务组件"。

  - **先算扇出计划（规模决定打法，不靠"感觉量大就多 spawn"）**：把 UI 源根交给 partition planner 算分区 / 批次 / 波次 / reduce / 采样计划，再照 `mode` 选打法：
    ```bash
    python3 .harness/common/skills/harness-setup/scripts/partition_plan.py \
      --root . --include 'components/**' 'src/**/components/**' 'src/**/features/**' \
      'app/**' 'pages/**' 'areas/**' 'Views/**' 'wwwroot/**' 'ui/**' 'web/**' \
      --partition-depth 2 --chunk 30 --concurrency 10 --threshold 150 --sample-cap 400 --json
    ```
    （`--partition-depth` 取到能切出"模块 / bounded-context"那一级——UI 根的二级目录通常就是模块，按项目实际调；`--include` 按实际 UI 根增删。）

  - **`mode=simple`（中小型）→ 按层分派（不靠主 agent 一遍范范扫）**：按设计系统分层把蒸馏拆成专注子任务，每个子 agent 只钻**一层**、在该层做机械抽取、逐条挂 source + status 回填。每个子 agent 输入 = generate-context 采集的设计语言信号 + 图谱里该层相关节点定位；输出 = 对应分层文件的填充草案 + 真值来源清单。**并行派发**以下子 agent：
    - **设计规范 / token 子 agent** → `design-spec.md`：解析全部 token 文件 / CSS 变量 / theme（**机械取真值，不脑补**），真值写 `prototype/tokens.css`、token 名登记进 `design-spec.md`；并抽出状态/反馈、内容/术语、领域对象表达、a11y/响应式四条横切维度的**现有**约定。**既有库项目**：token 真值优先取项目对库的**主题定制层**（Element 的 SCSS 变量 override / antd `theme.token` / ConfigProvider / 全局 CSS 变量），标 `source: lib-theme` 指明定制文件；库的默认 token 不抄进来。
    - **基础组件子 agent** → `base-components.md`：**先按「来源归属」分流**——①命中 **npm 包库**（组件住 `node_modules`，如 Element/antd/MUI）则**不复制、不逐个蒸全状态副本**，登记进 `base-components.md` 的「既有组件库 / 设计系统底座登记段」（库 @ 版本、被用组件清单、项目主题定制层、二次封装），库本身是其单一真相源；②**仓库内 vendored 组件**（项目持有源码，如 shadcn 风格 `components/ui/`）与**项目自研控件**才进 `BC-*` 目录，逐个抽 构成 / 变体 / **全状态矩阵**（非只默认态，与行为图 page-states 对齐）/ 用到的 token（与登记 token 不一致标 ⚠ 待对齐）/ 实现路径；二次封装在 `构成` 列注明所封装的库组件（如 `包 el-button`）。组件实现真值落 `prototype/components/base/`。**严禁把 Element/antd 这类 npm 包库组件当"真实渲染组件"蒸出一套和库官方打架的副本。**
    - **整体交互框架子 agent** → `interaction-framework.md`：观察应用外壳（header / nav / content / global 各 `SHELL-*` 区域）+ 全局导航 / 路由 / 跨 surface 浮层模式 / 全局状态与兜底。
    - **业务组件子 agent** → `business-components.md`（**有复现的领域-场景单元才派**）：盘点复现的领域-场景 UI 单元，绑上游 OBJ/SUC（**traces_to 不悬空**，引用的 SUC/OBJ 上游缺失则标「待补」、不自造）、组成引 `BC-*`；实现落 `prototype/components/business/`。无明确复现单元则不派，业务组件留给各 UI mission 逐个沉淀。
    - **设计原则不交纯机械子 agent**：产品气质需要观察 + 问用户确认，由主 agent 起草 `principles.md` 草案再与用户对齐，不靠脑补硬填。

  - **`mode=partitioned`（超大型）→ 按模块 map-reduce（按层一把扫会爆上下文，必须分区 + 分层 reduce）**：
    - **map（按 planner 的 `partitions`，照 `waves` 一波波派；按 `priority_rank` 先扫高价值模块）**：每个分区一个子 agent，**只钻一个模块**，在该模块内做全分层机械抽取（token / 基础组件 / 交互框架 / 业务组件），把该模块 design-system 草案**落盘**到 `harness-runtime/harness/artifacts/<id>/setup/design-system-staging/<module>.md`。**staging 草案必须真写到盘上**——它的存在就是 map 真发生过、不是空转的证据（Step 4 验证会查）。
    - **采样纪律（observe→condense，不穷举）**：planner 给了 `sampling` 时，按 `dominant_partitions` 优先覆盖主导模块到 `sample_cap` 即可收敛 canonical；尾部低价值模块留作各 UI mission 增量沉淀，不强行读每个文件。**被采样跳过的尾部模块必须在收尾报告 log 出来**，不静默截断。
    - **reduce（按 planner 的 `reduce_plan.strategy`）**：
      - `single` → 一个 reduce 步骤把全部 module 草案**按层合并 → 去重 → canonical**，落最终 `design-system/*.md` + `prototype/tokens.css`。
      - `hierarchical`（分区多于并发）→ 先把 module 草案按 `group_count` 分组，每组一个 reduce 子 agent 产出**组级小结**（staging/group-<k>.md），主 orchestrator 再合并组级小结 → canonical。**绝不在单个上下文里一把合所有 module 草案**——那正是超大型蒸馏真正的瓶颈所在。
      - 合并纪律不变：冲突标「⚠ 冲突 + 待人决策」、每条挂 source + status、禁止造值。
    - 设计原则（`principles.md`）仍由主 agent 起草 + 问用户，不进 map。

  - **综合 + 组件库展示页**：子 agent / reduce 返回后，主 agent 合并去重成一小份 canonical 集（冲突标「⚠ 冲突 + 待人决策」，不取默认值），落 `prototype/tokens.css` + `prototype/components/`，并**装配组件库展示页 `prototype/component-library.html`**——它 import `tokens.css`，把每个基础组件 / 业务组件按 **变体 × 全状态矩阵**逐个渲染出来供人直接看，每个实例打 `data-basecomp` / `data-bizcomp`（外壳示例打 `data-shell`），锚点须命中 `design-system/` 目录。它是设计系统的**可视化对账面**：人一眼看清蒸馏出了哪些组件、各有哪些状态，比只读 markdown 表格直观。
    > 边界区分：`component-library.html` 是设计系统**参考展示页**，按组件 / 状态分区陈列是其本职，**不受**"原型不许 gallery 堆叠"（prototype-standard R4）约束；它**不是** SUC 原型——SUC 原型仍按 R4 走真实交互、一次一态，不得用本页替代或混入。
  - 产出汇总：`project-knowledge/product/design-system/` 各层初版（`principles` / `interaction-framework` / `base-components` / `design-spec`；业务组件有复现单元才初版、否则留给各 UI mission）；`prototype/tokens.css`（token 真值）+ `prototype/components/`（组件实现）+ `prototype/component-library.html`（可视化展示）。
  - 纪律：**observe → condense**——借 graphify 图谱 + generate-context 采集的设计语言信号，从产品真实呈现观察主导用法（代码 token 文件 / theme / 组件库 / `materials/design/`），规范化成一小份 canonical 集；**机械抽取优先于总结**（能解析的 token 文件就解析取真值，不靠脑补）；**每条挂 source + status，禁止无来源造值**（没抽到标「待补」，冲突标「⚠ 冲突 + 待人决策」，绝不填默认值）。
  - **不是描述设计系统、也不是指向庞大原系统，是提炼出紧凑可消费的一小份。** 无来源（无既有设计语言）则保留 init 占位 + 不生成空展示页，由首个 UI mission 起草。
  - 这与 `/harness-upgrade` 的 OP-DS-001（既有项目升级到引入 design-system 能力时的回填）是同一蒸馏程序（同样分层子 agent 提取 + 组件库展示页），只是触发时机不同（首装 vs 升级）。
</step>

<step n="4" goal="完整性验证（含冒烟）">
  逐项按"预期"判断，不要求全 `PASS`：

  | 检查 | 命令 | 预期 |
  |---|---|---|
  | 项目上下文 | `harness context check --json` | `status: PASS` |
  | 项目知识库 | `harness knowledge check --json` | `status: PASS` |
  | 图谱 | `harness graphify status --json` | 既有项目 `available: true`；全新项目 `available: false`（正常） |
  | 控制面 | `harness control status --json` | 无任务时 `BLOCKED` 属正常，只需 `runtime_layout.mode = installed_project` |
  | 设计系统蒸馏（既有项目） | 对照 generate-context 的 `ui_presence` | `confirmed_ui` → `project-knowledge/product/design-system/` 各层有真值或「待补」占位（**空 = 缺项，回 Step 3 补蒸馏**）；`no_signal` + 用户确认无界面 → 空属正常，但收尾报告须有确认记录 |

  - 冒烟：确认 `skill-router` 能在本项目路由（读取 `.harness/common/skills/skill-router/` 存在即可）。
  - **设计系统空 ≠ 自动正常**：`ui_presence=confirmed_ui` 却没蒸馏，是缺项，必须回 Step 3 补，不得在验证里写"非 UI 项目正常"把缺项洗白放行。
  - **超大型项目（Step 3 走了 `mode=partitioned`）额外查**：`design-system-staging/` 下有 module 草案（map 真发生过的证据，非空转）；收尾报告 log 了被采样跳过的尾部模块清单（不静默截断）。缺 staging 草案而最终文件却"满了" = 可疑直填，回 Step 3 复核。
  - 有缺项 → 回对应步骤补跑（这就是 `re-init`），不要带病移交。
</step>

<step n="5" goal="移交">
  - 提示用户：把 Harness 安装资产纳入版本控制让团队共享——`.harness/`、`harness-runtime/`（运行数据除外按需）、`project-knowledge/`、adapter 入口（`AGENTS.md` / `CLAUDE.md` / `.claude/` 等）、`project-context.md`、`graphify-out/` 图谱本体；本地文件（`config.json`、token cache、`graphify-out/cache|manifest|cost`）保持 gitignore。
  - 告诉用户接下来怎么用：在 IDE 会话里直接用自然语言描述任务（`intake` 会自动接入），"继续"恢复任务，"当前任务到哪一步了"查状态。
  - 收尾报告：模式、已完成步骤、跳过项与原因、验证结果。
</step>

<step n="6" goal="升级 / 加 adapter（编排到权限化命令，不重写）">
  - 两类都需要从上游 git 仓库 `release` 分支取新模板（同 INSTALL.md「获取 Harness 源码」），把克隆目录作为 upstream source 传给命令。
  - 按用户意图导到对应命令，由其权限化 operation + Decision Gate 执行；**本技能不直接改框架正文 / runtime 结构 / adapter 入口**：
    - 升级到新版本模板（框架正文 + runtime 结构 + `harness.yaml` 三方迁移，可断点续跑的升级 checklist） → `/harness-upgrade`
    - 追加 AI 工具入口 → `/harness-add-adapter`
  - 受保护路径（`harness-runtime/harness/**`、`project-knowledge/**`、`materials/**`）默认只读，命令只能新增不能覆盖。
  - `harness.yaml` 升级由 `/harness-upgrade` 内部调 `harness config diff/migrate` 做三方迁移（保留 `project_name` / `brownfield` / 各开关），绝不重跑 `install.py --force`。
  - 特别提醒：graphify 升级后，`graphify-build` 是 vendored 副本，需按其文件头说明重新 vendored（随框架正文一起走 `/harness-upgrade`）。
</step>

</workflow>

---

## 错误处理

| 情况 | 处理 |
|---|---|
| CLI 不存在（无 `harness-runtime/bin/harness`） | 回 INSTALL.md 先跑 clone + `install.py`，不在本技能里 scaffold |
| `context init` FAIL | 报告错误（多为目录权限 / 模板缺失），修复后重试，不跳过 |
| `knowledge check` FAIL | 报告缺失结构；**不要 `knowledge init`**，按提示补结构或回 `install.py` 检查 scaffold |
| graphify CLI 装不上 | 记录原因；既有项目在 discovery 的 `degradations[]` 会记 `graphify_unavailable` 兜底，但应尽量装上 |
| 建图无 AI 会话可用（纯 CI） | 退回 `graphify extract` 自带 backend + Key（TokenHub: https://tokenhub.800best.com/ ）；有会话则不该走这条 |
| 已安装却被要求重装 | 转 `re-init`（补缺项）或更新类命令，绝不重跑 `install.py` 覆盖 |
