"""HarnessV2 hook package.

A single dispatcher (`dispatch.py`) is registered as the Claude Code
PreToolUse / PostToolUse hook entry. It resolves the active mission stage and
runs only that stage's checks, in-process — replacing the legacy model of one
standalone script per check registered globally in settings.json.

Layout:
  context.py   HookContext / payload parsing
  result.py    HookResult (allow | block)
  registry.py  stage -> event -> [HookEntry]
  dispatch.py  entry point
  lib/         shared helpers (contracts, commands, runtime, paths, roles)
  checks/      per-stage check functions
"""
