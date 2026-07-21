#!/usr/bin/env python3
"""Compatibility entrypoint for the Harness toolchain probe."""

from __future__ import annotations

from tdd_evidence_probe import build_probe, find_latest_mission, load_json, main, read_text  # noqa: F401


if __name__ == "__main__":
    raise SystemExit(main())
