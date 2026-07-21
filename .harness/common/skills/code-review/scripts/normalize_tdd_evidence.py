#!/usr/bin/env python3
"""Deprecated compatibility wrapper for normalize_toolchain_status.py."""

from __future__ import annotations

from normalize_toolchain_status import main, normalize  # noqa: F401


if __name__ == "__main__":
    raise SystemExit(main())
