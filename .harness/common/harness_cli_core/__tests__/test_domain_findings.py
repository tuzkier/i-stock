"""Unit tests for `harness_cli_core.domain.findings`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.findings import (  # noqa: E402
    apply_compat_warning,
    finding,
    is_placeholder_text,
    strict_status,
)


def test_finding_builds_dict_with_extras() -> None:
    f = finding("FAIL", "C-1", "boom", path="a/b.md", line=42)
    assert f == {
        "level": "FAIL",
        "code": "C-1",
        "message": "boom",
        "path": "a/b.md",
        "line": 42,
    }


def test_strict_status_pass_when_no_fail() -> None:
    status, failed = strict_status([{"level": "WARN", "code": "x"}])
    assert status == "PASS"
    assert failed == []


def test_strict_status_fail_when_any_fail() -> None:
    findings = [
        {"level": "WARN", "code": "w"},
        {"level": "FAIL", "code": "f"},
    ]
    status, failed = strict_status(findings)
    assert status == "FAIL"
    assert failed == [{"level": "FAIL", "code": "f"}]


def test_is_placeholder_text_recognises_common_markers() -> None:
    assert is_placeholder_text("")
    assert is_placeholder_text(None)
    assert is_placeholder_text("{{ todo }}")
    assert is_placeholder_text("N/A")
    assert is_placeholder_text("TBD")
    assert is_placeholder_text("不适用")
    assert is_placeholder_text("无")
    assert not is_placeholder_text("real content")


def test_apply_compat_warning_downgrades_fail_to_warn() -> None:
    args = argparse.Namespace(compat=True)
    findings = [
        {"level": "FAIL", "code": "x"},
        {"level": "WARN", "code": "y"},
    ]
    status, failed = apply_compat_warning(args, findings)
    assert status == "WARN"
    assert failed == []  # nothing reported as failed when compat
    # downgraded finding is marked
    assert findings[0] == {"level": "WARN", "code": "x", "compat_downgraded": True}


def test_apply_compat_warning_normal_mode_returns_fails() -> None:
    args = argparse.Namespace(compat=False)
    findings = [{"level": "FAIL", "code": "x"}]
    status, failed = apply_compat_warning(args, findings)
    assert status == "FAIL"
    assert failed == [{"level": "FAIL", "code": "x"}]


def test_apply_compat_warning_no_compat_attr_treated_as_false() -> None:
    args = argparse.Namespace()
    status, failed = apply_compat_warning(args, [{"level": "FAIL", "code": "x"}])
    assert status == "FAIL"
    assert failed == [{"level": "FAIL", "code": "x"}]
from harness_cli_core.app.parser import add_common, root_arg, with_json

__all__ = ["add_common", "root_arg", "with_json"]
