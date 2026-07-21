# Project Context

> **来源**：Harness context init + 当前仓库文件核对
> **目的**：记录所有 AI 执行者必须长期遵守的项目级约束。只写项目特有、容易被忽视、会影响执行正确性的事实。

**Author:** Codex
**Date:** 2026-05-23
**Project:** MyInvestment 看盘系统
**Status:** `active`

---

## 项目概览

| 字段 | 值 |
|------|----|
| 项目类型 | greenfield |
| 主要语言 | TypeScript / JavaScript |
| 主要框架 | React 19 + Vite 7 + Express 5 |
| 包管理器 | npm |
| 运行入口 | `npm run dev` |
| 测试入口 | 当前无独立 test script；质量检查使用 `npm run build` |

本项目是本地运行的多市场股票看盘系统，覆盖美股、港股、A 股、韩股的自选、K 线、常用技术指标、综合买卖信号和提醒规则。行情代理优先读取 Yahoo Finance；上游限流或不可用时允许返回演示 K 线，以保证界面、指标和提醒规则可测试。技术分析信号只用于提醒，不构成投资建议。

---

## 架构约束

| 约束 ID | 规则 | 适用范围 | 证据 / 来源 |
|---------|------|----------|-------------|
| ARCH-001 | 前端运行态由 Vite/React 承载，后端只承担本地 Express 静态服务与行情代理职责。 | `src/`、`server/` | `package.json`、`README.md` |
| ARCH-002 | 股票代码归一化必须遵守 Yahoo Finance 代码格式；纯数字输入按市场规则补后缀。 | watchlist、行情查询、提醒规则 | `README.md` |
| ARCH-003 | 技术信号应向 `MTS` 多周期趋势评分模型演进，避免把早期“四因子共振指标”扩展成长期单一判断口径。 | `src/lib/signals.ts`、指标展示、提醒逻辑 | `README.md`、`docs/technical-signal-research-design.md` |

---

## 编码规范

| 约束 ID | 规则 | 示例 / 说明 | 违反风险 |
|---------|------|-------------|----------|
| CODE-001 | 用户可见文案默认中文，金融缩写、股票代码、指标名可保留英文。 | RSI、MACD、ATR、EMA、AAPL | 原型和产品语义不一致 |
| CODE-002 | 本地持久化以浏览器 `localStorage` 为边界，不假设已有账号、云同步或服务端数据库。 | 自选股、提醒规则 | 提前引入不在范围内的账号/数据模型 |
| CODE-003 | 行情不可用时的演示数据必须明确提示，不能伪装为真实行情。 | Yahoo Finance 限流 fallback | 投资场景误导用户 |

---

## 技术选择

| 场景 | 默认选择 | 禁止 / 避免 | 理由 |
|------|----------|-------------|------|
| K 线渲染 | `lightweight-charts` | 手写 canvas K 线核心能力 | 已有成熟库依赖 |
| UI 图标 | `lucide-react` | 手写常见工具图标 | 与依赖和前端约定一致 |
| 质量检查 | `npm run build` | 只做静态阅读后宣称通过 | 当前无 test script，build 覆盖 TypeScript 与 Vite 构建 |
| 行情源 | Yahoo Finance 代理 + 明示 fallback | 隐式真实交易数据承诺 | README 已声明正式使用需授权行情供应商 |

---

## 测试约定

| 层级 | 命令 | 测试路径 | 说明 |
|------|------|----------|------|
| unit / integration | 暂无 | 暂无 | 当前 `package.json` 未定义 test script |
| lint / typecheck | `npm run build` | `src/`、`server/` | 执行 `tsc --noEmit && vite build` |
| e2e | 暂无 | `tests/e2e` 预留 | Harness 配置使用 Playwright，但项目尚未落地 e2e |

---

## 运行时环境

| 检测项 | 当前值 | 获取方式 | 备注 |
|--------|--------|----------|------|
| OS / Arch | Darwin 25.5.0 arm64 | `uname -a` | 本地 macOS |
| Node | v23.9.0 | `node -v` | npm 11.7.0 |
| Python | Python 3.13.2 | `python3 --version` | Harness CLI 可用 |
| Git | git version 2.39.2 | `git --version` | 当前项目目录不是 Git 仓库 |
| Docker | Docker version 29.4.0 | `docker --version` | 当前任务未依赖 Docker |

---

## Git 约定

| 项 | 约定 |
|----|------|
| 默认分支 | 未配置；当前目录不是 Git 仓库 |
| mission 分支格式 | 暂无 |
| stage worktree 根目录 | 当前项目根目录 + `harness-runtime/harness/stages/<mission-id>/` |
| 提交信息格式 | 暂无 |
| 推送 / PR 约定 | 暂无 |

---

## 已知风险与坑

| ID | 场景 | 风险 | 正确处理 |
|----|------|------|----------|
| PIT-001 | Yahoo Finance 限流或不可用 | 用户误把演示 K 线当真实行情 | fallback 必须有可见提示，并在设计/验证中单独覆盖 |
| PIT-002 | 多市场数字代码自动补后缀 | 港股、A 股、韩股都可能使用数字代码，归一化规则冲突 | UI 必须让用户看见最终解析出的代码和市场 |
| PIT-003 | 投资信号展示 | 技术指标容易被理解为交易建议 | 所有强买/强卖/评分文案必须保留“提醒/技术分析”边界 |

---

## 历史教训

| 日期 | 来源 mission | 教训 | 后续规则 / 影响 |
|------|--------------|------|-----------------|
| 2026-05-23 | 20260522-stock-watch-system | Interaction 阶段依赖根 `project-context.md`，只有 `project-knowledge/context/*` 不足以通过 `context.check`。 | 新 Mission 进入设计/交互前先运行 `harness context check`，缺失时用 CLI 初始化并补齐项目特有上下文。 |
- 2026-06-07 使用 Playwright no-webserver 配置验证本地前端时，必须先确认目标 dev server 端口已监听；ERR_CONNECTION_REFUSED 先按环境前提失败处理，不能直接判为产品行为失败。 (source: 20260522-stock-watch-system)
- 2026-06-07 Delivery gate 不是只看交付文档是否完整；delivery.contract.yaml 必须先通过通用 contract check，且 contract 模板、runtime 文件和 stage-gate checker 的 delivery_contract 注册必须保持一致，否则会在用户验收后阻断阶段推进。 (source: 20260522-stock-watch-system)
- 2026-06-07 晚轮 review-driven 修复也需要独立 red/regression 证据并刷新 toolchain/e2e/project_lint 派生快照；只保留最终 PASS 会降低后续审计和复盘信号质量。 (source: 20260522-stock-watch-system)
