# dashboard（仪表盘 / 看板总览）

> **何时用**：用户主任务是「快速感知一组指标 / 实体的整体状态」，再下钻到细节。强调可扫描的卡片网格与重点突出。

## 区域树（paste-ready）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-`<SURF>`-header | `<SURF>` | root | row | secondary | header | 标题 / 时间范围 / 全局操作 | 1 |
| R-`<SURF>`-filters | `<SURF>` | root | row | tertiary | filters | 范围 / 维度切换（诱发 system_event 的 via 控件） | 2 |
| R-`<SURF>`-kpi | `<SURF>` | root | row | primary | content | 关键指标卡（少而重） | 3 |
| R-`<SURF>`-grid | `<SURF>` | root | grid | primary | content | 图表 / 列表卡片网格 | 4 |

## 主次 / 扫描动线默认

- 顶部 KPI 区最重（primary，少量大数字），grid 承载明细卡。
- 扫描动线：header → filters → KPI → grid，自上而下、重点先行。
- 维度 / 时间范围切换是 system_event 的 `via` 控件（产品输入诱发不同结局），放 filters 区。

## 状态落区提示

- 每张卡独立 loading / empty / error（局部失败不拖垮整页）。
- 无数据时 KPI 区与 grid 区各自空态，引导去配置数据源。

## 典型坑

- ❌ 把几十个指标平铺成一堵卡墙——区分 KPI（少而重）与明细 grid，建立层级。
- ❌ 用 dev 开关切"有数据/无数据"——用 filters 区的数据范围 / 数据源切换诱发（声明 `edge.via`）。
- ❌ 卡片信息密度一致、没有主次——primary KPI 与 tertiary 辅助信息要分级。
