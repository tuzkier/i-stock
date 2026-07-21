"""Per-stage hook check modules.

Each module exposes `ENTRIES: list[HookEntry]` — the checks for one mission
stage. `registry.py` assembles them into the dispatch registry.
"""
