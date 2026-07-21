"""Unit tests for `harness_cli_core.domain.discovery`."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.discovery import (  # noqa: E402
    DEPENDENCY_TRIGGER_KEYWORDS,
    GRAPHIFY_INDEX_FRESH_HOURS,
)


def test_freshness_window_is_24_hours() -> None:
    assert GRAPHIFY_INDEX_FRESH_HOURS == 24


def test_dependency_trigger_keywords_are_pairs() -> None:
    assert all(
        isinstance(entry, tuple) and len(entry) == 2 for entry in DEPENDENCY_TRIGGER_KEYWORDS
    )
    assert all(
        isinstance(phrase, str) and isinstance(signal, str)
        for phrase, signal in DEPENDENCY_TRIGGER_KEYWORDS
    )


def test_dependency_trigger_signals_are_closed_set() -> None:
    signals = {signal for _phrase, signal in DEPENDENCY_TRIGGER_KEYWORDS}
    assert signals == {
        "data_model",
        "schema_change",
        "data_migration",
        "ddl_change",
        "external_system",
        "external_api",
        "integration",
        "infrastructure",
    }


def test_dependency_trigger_keywords_cover_known_signals() -> None:
    phrase_by_signal: dict[str, set[str]] = {}
    for phrase, signal in DEPENDENCY_TRIGGER_KEYWORDS:
        phrase_by_signal.setdefault(signal, set()).add(phrase.lower())
    # Spot-check the signals that the discovery handler relies on most.
    assert "migration" in phrase_by_signal["data_migration"]
    assert "schema" in phrase_by_signal["schema_change"]
    assert "external system" in phrase_by_signal["external_system"]
    assert "webhook" in phrase_by_signal["integration"]
    assert "ci/cd" in phrase_by_signal["infrastructure"]
