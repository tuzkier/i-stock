# materials/ — 外部录入资料区

> 项目根的**人提供原始资料**目录。团队从外部带进来的、harness 不自己生成的资料都放这里：
> 设计系统 / 品牌规范、外部接口文档、领域文档 / 业务规则、样例数据、调研 / 竞品材料、截图等。
> 它是 mission 的**输入真相**，被任务契约的 `source_materials` 按相对路径点名引用，被各阶段审查员
> 作为「原始材料」核对上游是否丢失诉求。

## 三个家，别混（关键）

| 目录 | 性质 | 谁写 | 谁读 |
|------|------|------|------|
| **`materials/`**（本目录） | **原始外部输入**，原样保存 | 人（团队录入） | 各阶段经 `source_materials` 引用 |
| **`project-knowledge/`** | harness **派生 / 蒸馏 / 沉淀**的结构化长期知识 | harness（promote / setup） | 各阶段 / 机器门 |
| stage artifacts（`harness-runtime/harness/artifacts/`） | 本次 mission 的阶段产出 | 各阶段 agent | 下游阶段 |

一句话：**原始资料进 `materials/`，蒸馏出的结构化基线进 `project-knowledge/`**。例如团队已有的设计系统原样放 `materials/design/`，蒸馏成 `project-knowledge/product/ui-design-system.md` 供 interaction / 组成门消费（注明 source 指回 material）。

## 不变量（机器与审查共同依赖）

1. **原始不可被 harness 覆盖**：本目录内容只有人能改 / 录入；任何 harness 命令、安装、更新都不得覆盖或删除（与 `project-knowledge/` 同级受保护）。
2. **provenance 必登记**：每份资料的来源、获取方式、对应落盘位置登记在 [`_sources.md`](_sources.md)。用户在对话里临时给的外部目录 / 链接 / 截图，先落盘 + 登记 `_sources.md`，再以 `materials/` 相对路径进入 `source_materials`；未落盘的临时材料不直接进 `source_materials`。
3. **按相对路径引用**：mission-contract 的 `source_materials` 是引用清单（`- materials/<path>：这份资料提供什么前提`），不复述全文。
4. **澄清沉淀机器写入**：`clarifications/` 由 `harness clarification record` 写入，是已确认澄清的沉淀，属文档集输入；不要手工乱放。
5. **蒸馏产物不留在这里**：从原始资料蒸馏出的 harness 可消费基线写进 `project-knowledge/`，不在 `materials/` 下另存一份。

## 推荐子目录（约定，非硬 schema）

materials 异构，按**资料种类**分目录便于引用与审查 provenance。按需建，不必铺满：

| 子目录 | 装什么 | 典型蒸馏去向 |
|--------|--------|--------------|
| `design/` | 设计系统 / 品牌规范 / Figma 导出 / 组件库文档 / UI 截图 / 视觉参考 | `project-knowledge/product/ui-design-system.md` |
| `api/` | 外部接口文档 / 契约 / schema / Postman / YAPI 导出 | dependency-impact / 接口知识 |
| `domain/` | 领域文档 / 业务规则 / 术语表 / 法规 / 规格 PDF | `project-knowledge/product/` 业务对象 / 术语 |
| `data/` | 样例数据 / 导出 / ER 图 / fixture | 数据建模 / 迁移依据 |
| `research/` | 调研 / 竞品 / 用户研究 / 需求文档 | 产品定义输入 |
| `clarifications/` | （机器写入）已确认澄清沉淀 | 文档集输入 |

其它种类自行加目录并在 `_sources.md` 说明。

## 与 source_materials 的关系

`source_materials`（任务契约）= 本次 mission 从 `materials/` 里**点名引用**的子集（按 mission 选取，不是全量）。`materials/` 是全量资料库；`source_materials` 是本次用到的那几份 + 用途说明。
