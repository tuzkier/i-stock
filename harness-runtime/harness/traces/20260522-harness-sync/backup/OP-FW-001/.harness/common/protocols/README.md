# 运行时协议索引

协议是控制面下按工程场景划分的操作规则。工作流在触发信号出现时引用对应协议；协议不替代 Stage Gate、审查员 Gate、命令证据或 Decision Gate。

```yaml
protocols:
 - id: quality-control
 path: .harness/common/protocols/quality-control/PROTOCOL.md
 triggers:
 - quality assessment request
 - stage-gate evidence 缺口
 - reviewer HOLD
 - acceptance evidence insufficiency
 primary_carrier: workflow_reference
 programmatic_carriers:
 - .harness/common/skills/stage-gate/scripts/check_contracts.py
 - .harness/common/skills/verify/scripts/collect_command_evidence.py
 - .harness/common/skills/harness-lint/scripts/check_runtime_consistency.py
 inferential_carriers:
 - code-review
 - verify
 - reviewer agents
 - id: bug-fix
 path: .harness/common/protocols/bug-fix/PROTOCOL.md
 triggers:
 - user reports bug
 - failing test indicates behaviour defect
 - verify AC failure caused by defect
 - runtime exception or crash
 primary_carrier: workflow_reference
 programmatic_carriers:
 - reproduction command
 - regression test command
 - .harness/common/skills/verify/scripts/collect_command_evidence.py
 inferential_carriers:
 - systematic-debugging
 - execute
 - reviewer agents
```

## 路由规则

如果同一个信号同时像缺陷和质量问题，先执行 `bug-fix`。质量结论必须基于已复现的缺陷、已验证无法复现的记录，或明确的证据状态。
