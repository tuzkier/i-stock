@AGENTS.md

---

## Claude Code Adapter

Use root `AGENTS.md` as the startup capsule. Do not preload `.harness/common/`, `.harness/docs/`, `.harness/common/agents/`, or all skill bodies at session start.

For routing, read `.harness/common/skills/skill-router/SKILL.md` and `workflow.md`; then read only the skill, rule, agent, script, or template files required by that workflow.

Harness role definitions are installed as native Claude Code subagents in `.claude/agents/<name>.md`. Load stage document rules, runtime config, and other Harness files only when the selected workflow, Gate, or user request requires them.

## Sub-agent dispatch on Claude Code

Claude Code's native subagent registry is `~/.claude/agents/<name>.md` and `<project>/.claude/agents/<name>.md`. The HarnessV2 installer materializes `.claude/agents/` from `.harness/common/agents/`, so every role file is discoverable as `subagent_type: <name>` immediately after install. Reinstall or rerun the install pipeline after upgrading Harness to keep the registry fresh.

The Task tool must dispatch named roles via `subagent_type` — do not collapse multiple required roles into a single generic invocation. If the registry is missing the role file (e.g. user deleted `.claude/agents/`), or the underlying Task tool refuses to dispatch the role, return BLOCKED to the calling workflow rather than executing the role inline. Inline execution by the main Agent is only allowed when the role's `model-routing` policy explicitly declares `fallback: main_agent`, and even then a `model_resolution` evidence record (with `fallback_used=main_agent` and reason) must be written. Reviewer-class roles never accept `main_agent` fallback.

## Skill workflow 副本路径（Claude-specific）

部分 skill workflow 的 subagent dispatch 已被 install pipeline 改写为 Claude Code 的 `Task(subagent_type=...)` 写法。读 skill workflow 时优先尝试 `.claude/skills/<skill>/workflow.md`（Claude-flavored，含具体 Task tool 调用）；该路径不存在时再 fall back 到 `.harness/common/skills/<skill>/workflow.md`（含 `<dispatch role="..." />` 占位符，需要自行用 Task tool 翻译）。
