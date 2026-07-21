# feed（信息流 / 时间线）

> **何时用**：用户主任务是「按时间序 / 推荐序浏览一串内容」，无限滚动或分页，可能有发布 / 筛选入口。

## 区域树（paste-ready）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-`<SURF>`-header | `<SURF>` | root | row | secondary | header | 标题 / 发布入口 / 切换 tab | 1 |
| R-`<SURF>`-filters | `<SURF>` | root | row | tertiary | filters | 分类 / 排序 / 范围（诱发 system_event 的 via） | 2 |
| R-`<SURF>`-stream | `<SURF>` | root | column | primary | content | 条目流（OBJ 列表，时间序） | 3 |
| R-`<SURF>`-aside | `<SURF>` | root | column | tertiary | detail | 辅助信息 / 推荐 / 趋势（可选） | 4 |

## 主次 / 扫描动线默认

- stream 是核心（primary，单列纵向滚动）；aside 为辅，窄屏可隐藏。
- 扫描动线：header → filters → stream（向下滚），aside 不打断主扫描。
- 加载更多 = action edge 或滚动触发；切换分类 = system_event（声明 `edge.via`）。

## 状态落区提示

- 初次加载：stream 区骨架；空态：stream 区引导（发布第一条 / 调整筛选）。
- 加载更多失败：stream 底部就近重试，不丢已加载内容。

## 典型坑

- ❌ 条目把所有字段铺满——条目只放扫描所需，详情进点击后的 page_state。
- ❌ 把 aside 做成与 stream 同权重的第二列——aside 是 tertiary，不抢主扫描。
- ❌ 用按钮假装"切换分类"却不接数据——分类切换是 system_event，需 `via` 控件。
