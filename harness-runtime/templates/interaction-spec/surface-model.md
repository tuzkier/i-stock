# 界面模型：{{mission_id}}

> **来源**：交互技能 → `harness-runtime/harness/artifacts/{{mission_id}}/interaction/interaction-spec/surface-model.md`
> **用途**：本文件是交互阶段固定标准包的一部分，负责定义真实系统界面边界、界面基线、信息架构和领域到界面的映射。它不替代 `interaction-contract.md`，而是为后续实现合同提供界面承载依据。

## 输入与来源

| 来源 | 已消费内容 | 缺口 / 回流 |
|------|------------|-------------|
| `../product/product-definition.md` | {{product_definition_refs}} | {{product_definition_gap}} |
| `../product/use-case-model.md` | 系统用例 `SUC-xx`、界面承载要求 | {{use_case_gap}} |
| `../product/business-object-analysis.md` | 业务对象 `OBJ-xx`、属性 `ATTR-xx`、状态机 `STM-xx`、业务规则 `BR-xx`（**对象轴主源**） | {{business_object_gap}} |
| `../product/acceptance-scenarios.md` | 验收场景 / 条件 `SCN-xx`、负向和边界路径 | {{acceptance_gap}} |
| `../product/product-domain-model.md` | DDD 领域模型（限界上下文 / 聚合 / 命令）；仅作 `OBJ→聚合` 交叉引用，**不作对象轴主锚** | {{domain_gap}} |
| `project-knowledge/product/ui-surfaces/` | 既有界面边界 `SURF-xxx` 基线（长期注册表 / ID 真源） | {{surface_knowledge_gap}} |

## 界面边界与变更

| 界面边界 | 限界上下文 / 导航节点 | 操作 | 基线引用 | 变更摘要 | 追溯 |
|----------|----------------------|------|----------|----------|------|
| SURF-001 | {{bounded_context}} | create_surface / modify_surface / extend_surface / retire_surface | {{baseline_ref_or_none}} | {{change_summary}} | {{trace_ref}} |

### 基线判定

| 问题 | 判定 | 证据 | 处理 |
|------|------|------|------|
| 是否已有界面承载同一用户目标 | yes / no / uncertain | {{evidence_ref}} | {{action}} |
| 是否会产生重复入口或重复页面 | yes / no / uncertain | {{evidence_ref}} | {{action}} |
| 非创建操作是否有稳定基线 | yes / no / n/a | {{baseline_ref}} | {{action}} |

## Surface 目录（机器段）

> **本表是 CLI 读取 surface 清单的权威机器段**，列顺序固定，被 `harness interaction prototype-check` 解析（`parse_surface_catalog`）：
> - `behavior-graph.yaml` 里每个 `page_state.surf` 必须命中本表的 surface id（否则 `GRAPH_PAGESTATE_SURF_UNKNOWN`）；
> - 每条 `edge.via`（`<surf>/<控件名>`）的控件名必须在对应 surface 的「via 控件清单」里声明，且原型有 `data-via="<surf>/<控件名>"` 元素。
> - `overlay` 叠加面拥有自己的 surface id，`page_entry` 指向宿主页 `#hash`。
> ID 一律引用上游真源（`SURF-xxx` 来自界面边界注册表），不得在本阶段新造。

| surface id | 名称 | 类型 | baseline 关系 | page_entry | via 控件清单 |
|------------|------|------|---------------|------------|--------------|
| SURF-BOARD | {{surface_name}} | page / overlay / component | create / modify / extend / retire | board.html | workspace-switcher, refresh-btn |

> **trace 脊柱已下沉行为图**：SURF↔SUC↔OBJ↔SCN↔state 的完整绑定现在以 `behavior-graph.yaml`（page_states / steps / edges / flows）为唯一真相源；旧的 `contracts/interaction.contract.yaml#surface_bindings` 已废弃。本文档只负责「有哪些 surface、IA、baseline」的容器轴 + 上面的机器段；拍 / 状态 / 连边一律在行为图里建。原型 HTML 锚点 `data-step` / `data-pagestate` / `data-via` 与行为图对账（`harness interaction prototype-check`）；`harness interaction resolve-feedback` 从行为图正向导航到承载某 SURF/SUC/OBJ/step 的 page_state。

## 布局骨架（机器段）

> **本表是 CLI 读取「页面怎么排」（组成轴）的权威机器段**，列顺序固定，被 `harness interaction prototype-check` 解析（`parse_region_catalog`）。它把每个 surface 的页面骨架定义成一棵**区域树**（线框颗粒：区域 × 嵌套 × 排布 × 优先级 × 角色 × 扫描序），不下到像素 / 具体控件样式。
>
> 它和行为图的分工：**行为图管「有哪些态、怎么流转」，本表管「页面怎么排」。** 缺了它，写 HTML 时整个空间排布是零约束的即兴 = 控件乱堆。
>
> 对账关系：
> - `behavior-graph.yaml` 里每个 `page_state.objects[].region` / `placements[].region` 必须命中本表的区域 id，且区域的「所属 surface」必须 == 该 page_state 的 surf（否则 `OBJECT_REGION_UNKNOWN` / `REGION_SURF_MISMATCH`）。
> - 某 surface 有 page_state 却在本表无任何区域 → `LAYOUT_REGION_MISSING`（FAIL）：这页没设计骨架。
> - 可见对象（`objects[].fields` 非空）没有 `region` → `OBJECT_UNPLACED`（FAIL）：控件无家可归。
> - 原型 HTML 须为承载内容的区域打 `data-region="<区域 id>"`；缺 → `REGION_NOT_RENDERED`（FAIL，与四方锚点同构）。
>
> 列定义（顺序不可变，解析器逐行按 `|` split + 首列正则 gate；表头 / 分隔行 / `{{...}}` 占位 / 散文行一律跳过）：
> - **区域 id**：匹配 `^R-[A-Z0-9][A-Za-z0-9_-]*$`（如 `R-BOARD-main`）。
> - **所属 surface**：必须命中上面的 surface 目录 surf id。
> - **父区域**：`root` 或本表已声明的另一个区域 id（→ 区域嵌套，构成树）。
> - **排布**：枚举 `row | column | grid | stack | flow`（stack = 叠加 / overlay 层）。
> - **优先级**：枚举 `primary | secondary | tertiary`（驱动主次层级与密度）。
> - **角色**：枚举 `navigation | content | detail | toolbar | actions | filters | status | header | footer`。
> - **默认承载**：本区**意图**承载的 OBJ / 动作组（自由中文，给人读的意图说明；实际逐态填充在行为图 objects/placements 的 region 里）。
> - **扫描序**：兄弟区域间的阅读 / 扫描顺序整数（编码主扫描动线；同父区域应唯一，缺则 `SCAN_ORDER_MISSING` WARN）。
>
> **基线优先（迭代系统必读）**：本表与行为图共享两层基线机制。
> - **新建 surface**（baseline=create）：先从 `.harness/common/skills/interaction/references/layout-patterns/` 选一个匹配的布局 pattern 作基底骨架（列表-详情 / 三栏主从 / 仪表盘 / 向导 / 表单 / 画布+inspector / 信息流 / 设置…），再按本 surface 实际承载裁剪——不要从白纸即兴排控件。
> - **改 / 扩既有 surface**（baseline=modify/extend）：必须**继承**项目级累积图 `project-knowledge/product/system-use-cases/behavior-graph.yaml#regions` 里该 surface 既有的区域树（及既有原型的 `data-region` 结构），本表只写**增量增改**，不重造骨架；既有区域被 prototype-check 回归校验（合并图里仍须被渲染），删除须在 behavior-graph 顶层 `retired:` 显式声明区域 id。
> - **贴合项目设计规范**：区域排布、主次、组件原语与交互约定必须遵循项目设计系统基线 `project-knowledge/product/ui-design-system.md`（间距 / 字阶 / 色彩角色 / 组件原语 / 布局与交互约定）；缺该文件时按 init 模板补，保证本次原型与既有界面一致、下游实现无歧义。

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-BOARD-toolbar | SURF-BOARD | root | row | secondary | toolbar | 刷新 / workspace 切换 | 1 |
| R-BOARD-main | SURF-BOARD | root | grid | primary | content | OBJ-01 节点列表 / 空态 CTA | 2 |

## N/A 豁免（机器段）

> **本表是 CLI 读取「非界面承载豁免」的唯一权威机器段**，列顺序固定，被 `harness interaction prototype-check` 解析（`parse_na_exemptions`）：
> - 凡某个 PRD 节点（SUC / 流步骤 / 节拍）**不需要任何界面承载**（纯后台批处理、纯外部系统集成、纯定时任务等无任何用户可观察界面的责任），在本表声明一行即可把它从 upstream 完整性分母里豁免；
> - **散文里不再写「不适用 / N/A / 非界面承载」+ SUC token 来豁免**——旧的关键词 grep 已废弃；scope-out（明确不提供的能力）写在「界面承载叙述」或 IA 表的叙述里，**不在本机器段**；本机器段只承载「PRD 已确认有此责任、但该责任不经界面体现」的豁免。
> - 声明了豁免但该节点其实已落入（合并）行为图 → 报 `NA_EXEMPTION_STALE`（FAIL，掩盖真实分母等价于绕过完整性门）。
> - 豁免一个 PRD 根本不存在的节点 → `NA_EXEMPTION_UNKNOWN_NODE`（WARN，拼写 / 陈旧引用提示）。
>
> 列定义（顺序不可变，解析器逐行按 `|` split + 首列正则 gate；表头 / 分隔行 / `{{...}}` 占位 / 散文行一律跳过）：
> - **PRD 节点 id**：必须匹配 `^(SUC-(?:TF-[A-Z]+-)?[0-9]+)(?:-FLOW-[0-9]+)?(?:\.[A-Za-z0-9_-]+)?$`，即 `SUC-07` / `SUC-TF-FOO-001` / `SUC-07-FLOW-02` / `SUC-07-FLOW-02.empty` 三种粒度形态之一。
> - **豁免粒度**：枚举小写 token `suc | flowstep | beat`，且必须与列 0 形态自洽（`suc`→无 `-FLOW`/无 `.state`；`flowstep`→含 `-FLOW` 无 `.state`；`beat`→含 `.state`），不自洽报 `NA_EXEMPTION_NODE_GRANULARITY_MISMATCH`；非枚举报 `NA_EXEMPTION_BAD_GRANULARITY`。
> - **理由**：自由中文，非空且非占位，否则报 `NA_EXEMPTION_INCOMPLETE`。
> - **责任归属**：自由文本（角色 / owner），同样非空非占位，否则报 `NA_EXEMPTION_INCOMPLETE`。
>
> 没有任何非界面承载责任时本表只保留表头与示例注释行（示例行用 `{{...}}` 占位，自动被解析器跳过），不要硬填。

| PRD 节点 id | 豁免粒度 | 理由 | 责任归属 |
|------------|----------|------|----------|
| {{na_node_id}} | suc / flowstep / beat | {{na_reason}} | {{na_owner}} |

<!-- 示例（实际豁免时复制此行并填真值，删除占位行）：
| SUC-07 | suc | 纯后台批处理用例，无任何用户可观察界面承载 | product-owner |
-->


### 界面承载叙述

> 每个界面边界用一段散文描述：这一屏给谁用、展示哪些业务对象（OBJ）、用户能做哪些动作（对应哪个 SUC / SUC-OP）、关键状态如何呈现。这是给人读的归属说明，与上表的机器 binding 互为表里。

- **SURF-001**：{{surface_narrative}}

## 信息架构

| 界面边界 | 核心对象（OBJ） | 支撑上下文 | 内容分组 | 主次动作 | 导航 / 返回 | 设计理由 |
|----------|----------------|------------|----------|----------|-------------|----------|
| SURF-001 | {{primary_object_obj_ref}} | {{supporting_context}} | {{content_groups}} | {{actions}} | {{navigation}} | {{rationale}} |

| 信息规则 | 适用范围 | 用户理解目标 | 追溯 |
|----------|----------|--------------|------|
| IA-001 | {{surface_or_flow}} | {{user_understanding}} | {{trace_ref}} |

## 业务对象到界面映射（OBJ 为主锚）

> 主锚是业务对象 `OBJ-xx` 及其属性 `ATTR-xx` / 状态机 `STM-xx`。每个被 PRD 标为用户可见的 OBJ 必须在某个 SURF 上"被体现"或写明"隐藏理由"；属性级映射支撑字段级覆盖校验（界面到底有没有显示 OBJ-01 的必显属性）。`OBJ→聚合` 一列只作给 solution / tech-design 的交叉引用，**不在 interaction 阶段强制对齐**（OBJ 与 DDD 聚合非 1:1）。

| 业务对象 / 属性 / 状态 | 承载界面边界 | 呈现方式 | 可见 / 折叠 / 隐藏理由 | OBJ→聚合 交叉引用（可选） | 追溯 |
|------------------------|--------------|----------|--------------------------|----------------------------|------|
| OBJ-01 / ATTR-01.. / STM-01 | SURF-001 | {{ui_expression}} | {{visibility_rationale}} | {{aggregate_xref_or_na}} | {{trace_ref}} |

## 权限、状态与错误承载

| 界面边界 | 领域规则 / 权限 | 用户可见状态 | 可用动作 | 禁用 / 拒绝反馈 | 恢复路径 |
|----------|----------------|--------------|----------|----------------|----------|
| SURF-001 | {{rule_or_permission}} | STATE-{{id}} | {{enabled_actions}} | {{blocked_feedback}} | {{recovery_path}} |

## 与实现合同的关系

| 本文件记录 | 下游合同位置 | 说明 |
|------------|--------------|------|
| Surface 绑定脊柱 | `../contracts/interaction.contract.yaml#surface_bindings` | binding 机器投影；原型锚点和 trace-coverage-check 的期望集来源 |
| 界面边界与变更 | `interaction-contract.md#路径状态与交互` | 路径和交互必须引用稳定界面边界 |
| 信息架构 | `interaction-contract.md#路径状态与交互` | 路径步骤不得绕开已定义导航和层级 |
| 业务对象到界面映射 | `interaction-contract.md#验证义务` | 验证义务必须断言用户可观察的 OBJ 结果 |
