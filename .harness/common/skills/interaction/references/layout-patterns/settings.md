# settings（设置 / 配置分区）

> **何时用**：用户主任务是「在分组的配置项里找到某项并修改」。左侧分区导航 + 右侧当前分区的配置表单。

## 区域树（paste-ready）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-`<SURF>`-nav | `<SURF>` | root | column | secondary | navigation | 设置分区列表（账户 / 通知 / 安全…） | 1 |
| R-`<SURF>`-section | `<SURF>` | root | column | primary | content | 当前分区的配置项 | 2 |
| R-`<SURF>`-section-actions | `<SURF>` | R-`<SURF>`-section | row | secondary | actions | 保存 / 还原（按分区） | 1 |

## 主次 / 扫描动线默认

- nav 选分区（secondary），section 是当前分区内容（primary）。
- 扫描动线：nav（选分区）→ section（改配置）→ 保存。
- 切换分区 = action edge；每个分区可为一个 page_state 或同 surface 的态切换。

## 状态落区提示

- 未保存改动：section-actions 区提示"有未保存更改"，离开前确认。
- 危险设置（删除账户 / 重置）：单独分区或显式二次确认 + 解释。
- 权限不足的设置项：禁用 + 说明，不静默隐藏。

## 典型坑

- ❌ 把所有设置堆成一长页——按分区切分，nav 导航。
- ❌ 一个全局保存按钮管所有分区——保存就近到当前分区（section-actions）。
- ❌ nav 分区按后端模块切——按用户心智 / 任务频率分组。
