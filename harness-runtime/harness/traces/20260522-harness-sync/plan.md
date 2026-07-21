# Harness Permissioned Change Plan

## Target

- Project root: `/Users/hanbin/Workspace/AI/MyInvestment`
- Requested change: 将当前 HarnessV2 源码工作区同步安装到已安装目标项目
- Created at: `2026-05-22 19:02:47 +0800`
- Upstream source: `/Users/hanbin/Workspace/AI/Harness搭建/HarnessV2`
- Upstream evidence:
  - `VERSION`: `1.1`
  - `git rev-parse --short HEAD`: `7b93e91`
  - `git status`: dirty working tree, includes framework, adapter, runtime template and app changes
- Target evidence:
  - installed Harness: yes, `.harness/common/rules/core.md` exists
  - target `harness_template.version`: `1.1`
  - target `harness_template.source_commit`: `1a0b215`
  - target git repository: absent
  - `harness control status --json`: PASS
  - `harness knowledge check --json`: PASS

## Decision

This is not a first install. The target already has Harness assets:

- `.harness/`
- `harness-runtime/`
- `project-knowledge/`
- `AGENTS.md`
- `CLAUDE.md`
- `.cursor/`
- `.claude/`

Because source and target both report version `1.1`, this is a same-version working-tree template sync, not a normal version-number upgrade. It still has real content differences because the target records source commit `1a0b215` and the upstream HEAD is `7b93e91`, with additional uncommitted upstream changes.

No replace or patch operation may run until the approved operation ids are filled below.

## Asset Classification

| Class | Paths | Operation | Permission Required | Risk | Rollback |
|---|---|---|---|---|---|
| A framework | `.harness/common/**`, `.harness/docs/**`, `.harness/workflow-map.html` | replace from upstream template, excluding generated/cache files | `approve-framework` | medium | restore backup for each op |
| B adapter entry | `AGENTS.md`, `CLAUDE.md`, `.cursor/**`, `.claude/**`, `.codex/**` | render/replace installed adapter entries only | `approve-adapter` | medium | restore backup for each op |
| C runtime structure | `harness-runtime/bin/**`, `harness-runtime/templates/**`, `harness-runtime/scripts/**`, `harness-runtime/config/**` | replace/patch structure assets; config is template-authoritative | `approve-runtime-structure` | high | restore backup for each op |
| D runtime data | `harness-runtime/harness/**` | read-only except this trace directory and backups | `approve-runtime-data` | critical | restore backup, do not mutate historical results |
| E project knowledge | `project-knowledge/**` | no operation proposed | not requested | high | not applicable |

## Proposed Operations

| ID | Path | Operation | Source | Why Needed | Verification | Status |
|---|---|---|---|---|---|---|
| OP-FW-001 | `.harness/common/**` | replace, excluding `.DS_Store`, `__pycache__`, `.pytest_cache`, `*.pyc` | `/Users/hanbin/Workspace/AI/Harness搭建/HarnessV2/package/common/**` | Sync rules, skills, agents, schemas and CLI framework content | `harness control status --json` | done `2026-05-22 19:11:19 +0800` |
| OP-DOC-001 | `.harness/docs/**` | replace | `/Users/hanbin/Workspace/AI/Harness搭建/HarnessV2/package/docs/**` | Sync installed Harness reference docs | sampled diff + `harness control status --json` | done `2026-05-22 19:11:19 +0800` |
| OP-DOC-002 | `.harness/workflow-map.html` | replace | `/Users/hanbin/Workspace/AI/Harness搭建/HarnessV2/package/workflow-map.html` | Sync visual workflow map | file exists and non-empty | done `2026-05-22 19:11:19 +0800` |
| OP-ADAPTER-001 | `AGENTS.md`, `CLAUDE.md`, `.cursor/**`, `.claude/**`, `.codex/**` | render/replace installed adapter entries only | `/Users/hanbin/Workspace/AI/Harness搭建/HarnessV2/package/adapters/**` | Keep Codex, Claude and Cursor entry points aligned with the synced framework | entry files exist; root instructions still point to `.harness/**` | done `2026-05-22 19:11:19 +0800` |
| OP-RUNTIME-001 | `harness-runtime/bin/**`, `harness-runtime/scripts/**`, `harness-runtime/templates/**` | replace structure assets, excluding runtime data under `harness-runtime/harness/**` | `/Users/hanbin/Workspace/AI/Harness搭建/HarnessV2/package/harness-runtime/{bin,scripts,templates}/**` | Sync CLI shim, scripts and stage/contract templates; current diff includes template additions/removals | `harness control status --json`; `harness knowledge check --json`; `harness knowledge index --json` | done `2026-05-22 19:11:19 +0800` |
| OP-CONFIG-001 | `harness-runtime/config/harness.yaml` | replace from current template; update `harness_template.source_commit` after sync | `/Users/hanbin/Workspace/AI/Harness搭建/HarnessV2/package/harness-runtime/config/harness.yaml` plus upstream git metadata | Align target runtime configuration with the current template; old config attributes are not preserved by default | YAML parse + `harness config snapshot --json` | done `2026-05-22 19:11:19 +0800` |

## Explicit User Approval

- Approved operation ids: OP-FW-001, OP-DOC-001, OP-DOC-002, OP-ADAPTER-001, OP-RUNTIME-001, OP-CONFIG-001
- Rejected operation ids:
- Accepted risks:
  - User approved overwrite update: "要 覆盖更新 接受无git"
  - Source working tree is dirty; approval means the current local upstream files, not only committed `7b93e91`, may be installed.
  - Target project is not a Git repository; rollback depends on per-operation backups in this trace directory.
  - This is a same-version sync (`1.1` -> `1.1`), so version number alone will not distinguish before/after state.

## Execution Notes

Before each approved operation, create a backup under:

`harness-runtime/harness/traces/20260522-harness-sync/backup/<op-id>/`

After approved operations, write command stdout to:

`harness-runtime/harness/traces/20260522-harness-sync/verify.log`

Required verification commands:

```bash
harness-runtime/bin/harness --root /Users/hanbin/Workspace/AI/MyInvestment control status --json
harness-runtime/bin/harness --root /Users/hanbin/Workspace/AI/MyInvestment knowledge check --json
harness-runtime/bin/harness --root /Users/hanbin/Workspace/AI/MyInvestment knowledge index --json
```

## Execution Summary

- Backup directory: `harness-runtime/harness/traces/20260522-harness-sync/backup/`
- Execution command: `python3 install.py /Users/hanbin/Workspace/AI/MyInvestment --force --adapter cursor --adapter claude --adapter codex --entry-policy overwrite`
- Execution result: PASS
- Executed at: `2026-05-22 19:11:19 +0800`

## Verification Summary

- Verification log: `harness-runtime/harness/traces/20260522-harness-sync/verify.log`
- `harness control status --json`: PASS
- `harness knowledge check --json`: PASS
- `harness knowledge index --json`: PASS
- `harness config snapshot --json`: PASS
- `harness lint runtime --json`: PASS
- Synced metadata: `harness_template.source_commit` = `7b93e91`

## Correction

- Corrected interpretation on `2026-05-23`: runtime config migration should be template-authoritative.
- `spec.enabled=true` is the intended template default and should remain true after migration.
- The earlier OP-CONFIG wording that favored target-side config was incorrect for template migration. Old `harness-runtime/config/**` attributes must not be preserved merely because they existed in the target.
- Project-specific decisions should live in `project-knowledge/**` or in explicit project-level configuration entry points declared by the current template.
