---
knowledge_type: product
status: draft
source: init
confidence: needs-review
---

# 整体交互框架

> 宏观层：所有 surface 都活在同一个**应用外壳 + 全局导航**里，按同一套**跨 surface 交互模式**和**全局状态**行为。它是区域树（单 surface 内布局）的宏观对位——区域树管"一屏内怎么排"，本文件管"所有屏在同一个壳和导航里怎么组织、怎么跳"。
> 蒸馏来源：观察产品真实外壳 + 导航结构 + `materials/design/`；setup 早期确立、很少改（全局且稳定）。每条带 source / status；无来源留占位，不凭通用最佳实践硬填。

## 应用外壳（机器段）

> 列顺序固定，供治理门解析（未来 `prototype-check` 的 design-system 类）。壳区域 id 形态 `^SHELL-[A-Za-z0-9][A-Za-z0-9_-]*$`；原型对应容器打 `data-shell="SHELL-…"`，每个 surface 都挂在同一套壳里（与 `data-region` 区域锚点同构）。表头 / 分隔行 / `{{…}}` 占位行跳过。

| 壳区域 id | 角色 | 承载 | source | status |
|-----------|------|------|--------|--------|
| {{SHELL-id}} | {{角色}} | {{承载}} | {{来源}} | draft |

<!-- 确立应用外壳时复制下列行填真值，删除占位行（占位行被解析器跳过 = 未采用）：
| SHELL-header | header | logo / 全局搜索 / 用户菜单 | 观察:主框架 | stable |
| SHELL-nav | navigation | 主导航，surface 组织入口 | 观察:主框架 | stable |
| SHELL-content | content | 当前 surface 挂载点 | 观察:主框架 | stable |
| SHELL-global | status | 通知 / toast / 全局浮层根 | 观察:主框架 | stable |
-->

## 全局导航与路由

> 散文，描述以下要点（无来源留"待补"）：

- surface 怎么组织成导航层级、用户怎么到达每个 surface。
- 面包屑 / deep-link / 返回·前进 / 跨 surface 导航时的上下文保持规则。

## 跨 surface 交互模式

- 浮层（弹窗 / 抽屉 / toast）的全局行为约定（在哪挂、怎么关、焦点怎么回）。
- 一个业务流程跨多个 surface 时怎么走、状态 / 上下文怎么带过去。

## 全局状态 / 反馈

- 应用级加载、错误边界（error boundary）、鉴权 / 权限闸、空态 onboarding、全局通知的统一表现。
- 这些是横切的全局兜底，单 surface 内的状态走 `design-spec.md` 的「状态与反馈 canonical」。
