---
knowledge_type: operations
status: draft
source: init
confidence: needs-review
---

# Verification Runbooks

Document stable verification commands and result interpretation.

## 本地看盘系统验收验证

来源：mission:20260522-stock-watch-system。状态：accepted。置信度：high。

| Command | When To Run | Expected Signal | Source |
|---|---|---|---|
| `npm run build` | 任一前端 / 领域逻辑交付进入验证前 | TypeScript 与 Vite build 退出码为 0 | `harness-runtime/harness/artifacts/20260522-stock-watch-system/verify/verification-report.md` |
| `node --test harness-runtime/harness/traces/20260522-stock-watch-system/t006-all-tests/*.mjs` | 复核冻结样本、MTS、提醒、恢复和 watchlist replay | 所有 replay/unit 用例 PASS | `harness-runtime/harness/artifacts/20260522-stock-watch-system/verify/verification-report.md` |
| `PORT=5174 npm run dev` + `playwright test --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list --trace=on` | 验证用户可观察路径和浏览器恢复路径 | 目标端口已监听后，E2E PASS；若端口未起，`ERR_CONNECTION_REFUSED` 是环境前提失败，不是产品行为失败 | `harness-runtime/harness/artifacts/20260522-stock-watch-system/delivery/delivery-package.md` |

## 解释规则

- no-webserver Playwright 配置不会自动启动 dev server；验证前必须显式确认 `http://localhost:5174` 可访问。
- live 行情不作为核心验收门禁；核心路径使用冻结样本和 replay corpus。
- 来源健康、demo fallback、stale、unavailable 必须在图表、MTS 和提醒区域穿透显示，不能只看命令退出码。
