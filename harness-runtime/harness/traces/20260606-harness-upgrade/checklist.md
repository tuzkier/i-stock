# Harness 升级 checklist — 20260606
源上游: /Users/hanbin/Workspace/AI/Harness搭建/HarnessV2   当前版本: 1.1 → 目标版本: 1.6

- [x] Phase 0 备份（harness.yaml → backup/phase0/）
- [x] Phase 1/2/4 框架正文 + runtime 结构资产 + adapter 重渲染（install.py --force，runtime mission 保留）
- [x] Phase 3 harness.yaml 三方迁移（config migrate，保留项目值）
- [x] Phase 6 验证：control status PASS / knowledge check PASS

## Upgrade Summary
- 框架体刷新到 1.6（含原型门控重设计 + 47 处方法补全）
- 项目值保留：见 config-decisions.yaml
