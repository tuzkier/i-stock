---
knowledge_type: lessons
status: draft
source: init
confidence: needs-review
---

# Quality Lessons

Quality-control findings that should influence future planning, review, or
verification.

## 20260522-stock-watch-system

来源：mission:20260522-stock-watch-system。状态：accepted。置信度：high。

- Delivery gate 依赖 contract 外壳、schema 注册和语义检查三者一致；交付包准备好后应先运行 `harness contract check --artifact harness-runtime/harness/stages/<mission>/contracts/delivery.contract.yaml --json`，再执行用户 handoff 或 stage gate。
- Review 内部 HOLD 与复审闭环不能只压缩成最终 PASS/PASS_WITH_RISK；复盘和 DORA 信号需要同时记录最终结论和实际摩擦，否则会低估晚阶段返工。
- 晚轮 review-driven 修复应保留独立 red/regression 证据；如果只在最终回归中证明通过，后续审计很难判断修前失败是否真实可捕获。
- 控制面派生快照（例如 project_lint、toolchain-status、e2e-status）滞后时必须在交付包中显式说明当前权威证据，并在后续流程中刷新快照。
