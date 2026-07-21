"""Unit tests for `harness_cli_core.domain.solution_lint`."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.solution_lint import (  # noqa: E402
    SOLUTION_ANTI_PATTERN_PHRASES,
    SOLUTION_VAGUE_MITIGATION,
)


def test_anti_pattern_phrases_are_triples() -> None:
    assert all(
        isinstance(entry, tuple) and len(entry) == 3
        for entry in SOLUTION_ANTI_PATTERN_PHRASES
    )


def test_anti_pattern_rule_codes_closed_set() -> None:
    rules = {rule for _phrase, rule, _msg in SOLUTION_ANTI_PATTERN_PHRASES}
    assert rules == {"anti_minimum_change", "anti_demo_first", "anti_temporary_plan"}


def test_anti_pattern_covers_chinese_and_english_minimum_change() -> None:
    phrases = {p for p, _r, _m in SOLUTION_ANTI_PATTERN_PHRASES}
    assert "最小改动" in phrases
    assert "改动最小" in phrases
    assert "minimum change" in phrases


def test_anti_pattern_covers_demo_first_variants() -> None:
    phrases = {p for p, _r, _m in SOLUTION_ANTI_PATTERN_PHRASES}
    # demo first appears in both "先 demo" and "先做demo" / "先做 demo" wording
    assert any("demo" in p.lower() for p in phrases)
    assert "demo 先行" in phrases


def test_vague_mitigation_contains_chinese_and_english_phrases() -> None:
    assert "考虑" in SOLUTION_VAGUE_MITIGATION
    assert "TBD" in SOLUTION_VAGUE_MITIGATION
    assert "later" in SOLUTION_VAGUE_MITIGATION


def test_vague_mitigation_is_all_strings() -> None:
    assert all(isinstance(phrase, str) for phrase in SOLUTION_VAGUE_MITIGATION)
