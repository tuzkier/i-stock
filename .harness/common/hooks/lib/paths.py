"""Glob path matching helpers."""

from __future__ import annotations

import fnmatch

_RUNTIME_PREFIX = "harness-runtime/harness/"


def normalize(path: str) -> str:
    """Forward-slash form, no leading ./"""
    out = (path or "").replace("\\", "/")
    while out.startswith("./"):
        out = out[2:]
    return out


def strip_runtime_prefix(path: str) -> str:
    """Drop a leading harness-runtime/harness/ so overlay-relative globs match."""
    out = normalize(path)
    if out.startswith(_RUNTIME_PREFIX):
        return out[len(_RUNTIME_PREFIX):]
    return out


def match(path: str, pattern: str) -> bool:
    """fnmatch with `**` treated as a multi-segment wildcard."""
    p = normalize(path)
    pat = normalize(pattern)
    if fnmatch.fnmatch(p, pat):
        return True
    # fnmatch already treats * as crossing /, so ** behaves like *; also try
    # a relaxed form where a trailing /** matches the directory itself.
    if pat.endswith("/**") and (p == pat[:-3] or fnmatch.fnmatch(p, pat[:-3] + "/*")):
        return True
    return False


def match_any(path: str, patterns) -> bool:
    return any(match(path, pat) for pat in (patterns or []))
