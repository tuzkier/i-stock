# wizard（向导 / 多步任务）

> **何时用**：用户主任务有**明确顺序的多个步骤**，需要引导逐步完成（onboarding、开通流程、复杂创建、迁移）。每步是一个 page_state，步骤进度常驻。

## 区域树（paste-ready）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-`<SURF>`-steps | `<SURF>` | root | row | secondary | navigation | 步骤进度指示（当前 / 已完成 / 未到） | 1 |
| R-`<SURF>`-stepbody | `<SURF>` | root | column | primary | content | 当前步骤的字段 / 内容 | 2 |
| R-`<SURF>`-stephelp | `<SURF>` | R-`<SURF>`-stepbody | column | tertiary | status | 当前步骤说明 / 校验反馈 | 1 |
| R-`<SURF>`-nav | `<SURF>` | root | row | secondary | actions | 上一步 / 下一步 / 完成 / 取消 | 3 |

## 主次 / 扫描动线默认

- stepbody 是每步的核心（primary）；steps 进度在顶（或左），nav 操作在底。
- 扫描动线：steps（我在哪）→ stepbody（做什么）→ nav（去哪）。
- 每个步骤 = 一个 page_state，步骤切换 = action edge（下一步/上一步）。

## 状态落区提示

- 校验失败：stephelp / stepbody 内就近显示，不丢已填数据。
- 步骤可达性：未完成前序步骤不能跳后续（非法转换在 nav 区禁用 + 反馈）。

## 典型坑

- ❌ 把所有步骤字段堆在一页用折叠面板——向导是逐步 page_state，不是长表单。
- ❌ 进度区只画静态条、不反映当前/已完成——steps 区状态要随 page_state 变。
- ❌ 失败后回到第一步丢全部输入——恢复路径必须保留已填内容。
