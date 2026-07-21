"""Unit tests for `harness_cli_core.domain.evidence`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.evidence import (  # noqa: E402
    evidence_store_path,
    load_evidence_store,
)


def test_evidence_store_path_explicit_wins(tmp_path: Path) -> None:
    explicit = tmp_path / "custom.json"
    assert evidence_store_path(tmp_path, "M-1", str(explicit)) == explicit


def test_evidence_store_path_defaults_to_traces(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    expected = runtime / "traces" / "M-1" / "evidence" / "evidence.json"
    assert evidence_store_path(tmp_path, "M-1") == expected


def test_load_evidence_store_returns_empty_when_missing(tmp_path: Path) -> None:
    store = load_evidence_store(tmp_path / "missing.json", "M-1")
    assert store == {"schema_version": 1, "mission_id": "M-1", "evidence": [], "links": []}


def test_load_evidence_store_filters_non_dict_items(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "mission_id": "M-X",
                "evidence": [{"id": "e1"}, "not-a-dict", {"id": "e2"}],
                "links": [{"from": "e1", "to": "ac1"}, 42],
            }
        ),
        encoding="utf-8",
    )
    store = load_evidence_store(path, "M-1")
    assert store["schema_version"] == 2
    assert store["mission_id"] == "M-X"  # uses the existing mission_id
    assert store["evidence"] == [{"id": "e1"}, {"id": "e2"}]
    assert store["links"] == [{"from": "e1", "to": "ac1"}]


def test_load_evidence_store_returns_default_when_evidence_is_not_list(
    tmp_path: Path,
) -> None:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"evidence": "not-a-list"}), encoding="utf-8")
    store = load_evidence_store(path, "M-1")
    assert store == {"schema_version": 1, "mission_id": "M-1", "evidence": [], "links": []}
