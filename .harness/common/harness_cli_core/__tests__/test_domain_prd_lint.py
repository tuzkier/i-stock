"""Unit tests for `harness_cli_core.domain.prd_lint`."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.prd_lint import (  # noqa: E402
    compute_ignore_lines,
    has_heading,
    is_na_with_reason,
    markdown_sections,
    scan_anti_patterns,
    scan_domain_model,
    section_has_content,
)


# ---------------------------------------------------------------------------
# compute_ignore_lines
# ---------------------------------------------------------------------------

def test_compute_ignore_lines_marks_fenced_block_including_markers() -> None:
    text = "outside\n<!-- prd-anti-pattern-ignore-start -->\ninside\n<!-- prd-anti-pattern-ignore-end -->\nback\n"
    ignored = compute_ignore_lines(text, "prd-anti-pattern-ignore")
    assert ignored == {2, 3, 4}


def test_compute_ignore_lines_empty_when_no_markers() -> None:
    assert compute_ignore_lines("a\nb\nc\n", "prd-anti-pattern-ignore") == set()


# ---------------------------------------------------------------------------
# markdown_sections / has_heading / section_has_content
# ---------------------------------------------------------------------------

def test_markdown_sections_splits_on_h2() -> None:
    text = "## A\nalpha\n\n## B\nbeta\n"
    sections = markdown_sections(text)
    assert set(sections.keys()) == {"A", "B"}
    assert sections["A"] == "alpha"
    assert sections["B"] == "beta"


def test_has_heading_true_for_any_level() -> None:
    assert has_heading("## State Machines\n", "State Machines")
    assert has_heading("#### State Machines\n", "State Machines")
    assert not has_heading("State Machines (no hash)\n", "State Machines")


def test_section_has_content_ignores_dividers_and_subheads() -> None:
    assert not section_has_content("\n---\n|---|---|\n### Sub\n")
    assert section_has_content("\nreal line\n")


# ---------------------------------------------------------------------------
# is_na_with_reason
# ---------------------------------------------------------------------------

def test_is_na_with_reason_true_for_non_na_line() -> None:
    assert is_na_with_reason("普通内容")


def test_is_na_with_reason_true_when_reason_present() -> None:
    assert is_na_with_reason("N/A 因为本任务不涉及该域")
    assert is_na_with_reason("n/a because no UI surface in scope")


def test_is_na_with_reason_false_for_bare_na() -> None:
    assert not is_na_with_reason("- N/A")
    assert not is_na_with_reason("不适用")


# ---------------------------------------------------------------------------
# scan_anti_patterns
# ---------------------------------------------------------------------------

def test_scan_anti_patterns_detects_vague_adjective() -> None:
    # English single-word path — splitter is whitespace, so the vague term
    # must appear as its own token.
    findings = scan_anti_patterns("- the system must be fast and intuitive\n")
    rules = {f["rule"] for f in findings}
    assert "vague_adjective" in rules


def test_scan_anti_patterns_detects_implementation_leak() -> None:
    findings = scan_anti_patterns("REQ-1: 使用 PostgreSQL 实现\n")
    rules = {f["rule"] for f in findings}
    assert "implementation_leak" in rules


def test_scan_anti_patterns_ignores_fenced_block() -> None:
    text = (
        "<!-- prd-anti-pattern-ignore-start -->\n"
        "PostgreSQL 在此处可以保留（术语表引用）\n"
        "<!-- prd-anti-pattern-ignore-end -->\n"
    )
    findings = scan_anti_patterns(text)
    assert not any(f["rule"] == "implementation_leak" for f in findings)


def test_scan_anti_patterns_flags_unmeasurable_trace_anchor() -> None:
    # Need > 10 chars after the colon; no digits and no Given/When/Then.
    text = "REQ-LOGIN: user should be able to access the dashboard\n"
    findings = scan_anti_patterns(text)
    assert any(f["rule"] == "unmeasurable" for f in findings)


# ---------------------------------------------------------------------------
# scan_domain_model
# ---------------------------------------------------------------------------

def test_scan_domain_model_flags_missing_section() -> None:
    findings = scan_domain_model("")  # entirely empty document
    codes = {f["code"] for f in findings}
    assert "missing_domain_model_section" in codes


def test_scan_domain_model_traces_requirements_into_traceability(tmp_path: Path) -> None:
    domain_text = (
        "## Domain Intent\nIntent\n\n"
        "## Strategic DDD\n### Bounded Contexts\nctx\n### Context Map\nmap\n### Ubiquitous Language\nlang\n\n"
        "## Tactical DDD\n### Aggregates\nagg\n### Domain Commands\ncmd\n### Domain Events\nevt\n"
        "### Invariants\ninv\n### State Machines\nsm\n\n"
        "## Rules & Constraints\nrules\n\n"
        "## Traceability\nREQ-A linked to Aggregate X\n\n"
        "## Downstream Guidance\nguide\n\n### Permission Matrix\nmatrix\n"
    )
    findings = scan_domain_model(domain_text, product_definition_text="REQ-A and REQ-B")
    codes = {(f["code"], f.get("evidence")) for f in findings}
    # REQ-A traced, REQ-B not
    assert ("untraced_requirement", "REQ-B") in codes
    assert ("untraced_requirement", "REQ-A") not in codes


def test_scan_domain_model_detects_invalid_state_machine_shape() -> None:
    text = (
        "## Tactical DDD\n### State Machines\nFrom State, To State, Trigger only\n"
    )
    findings = scan_domain_model(text)
    codes = {f["code"] for f in findings}
    assert "invalid_state_machine_shape" in codes
