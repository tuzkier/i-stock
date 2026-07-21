# form（录入 / 编辑表单）

> **何时用**：用户主任务是「录入或编辑一组字段并提交」。单步、字段较多、需分组与校验反馈。

## 区域树（paste-ready）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-`<SURF>`-header | `<SURF>` | root | row | secondary | header | 表单标题 / 说明 | 1 |
| R-`<SURF>`-body | `<SURF>` | root | column | primary | content | 字段分组（按语义） | 2 |
| R-`<SURF>`-group-primary | `<SURF>` | R-`<SURF>`-body | column | primary | content | 必填 / 核心字段组 | 1 |
| R-`<SURF>`-group-advanced | `<SURF>` | R-`<SURF>`-body | column | tertiary | content | 高级 / 可选字段组（默认折叠） | 2 |
| R-`<SURF>`-actions | `<SURF>` | root | row | secondary | actions | 提交 / 取消 / 重置 | 3 |

## 主次 / 扫描动线默认

- body 是核心；按**语义**分组而非按数据库表分组。核心组在前、可选组折叠。
- 扫描动线：header → 核心字段 → 高级（按需展开）→ actions。
- 主操作（提交）在 actions 区固定位置，危险操作（重置）需二次确认。

## 状态落区提示

- 字段级校验：错误就近显示在字段下，不集中堆顶部。
- 提交中 / 成功 / 失败：actions 区或 header 区给整体反馈；失败不丢输入。
- 权限不足字段：禁用 + 解释，不隐藏导致用户困惑。

## 典型坑

- ❌ 把领域字段机械平铺成一长列——必须按语义分组、核心在前。
- ❌ 所有字段一视同仁——必填/核心 vs 可选/高级要分区与优先级。
- ❌ 校验错误只在提交时弹一个汇总——应字段级就近反馈。
