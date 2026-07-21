"""Pure helpers for reviewer selection.

The code-review *contract* loader lives in
``harness_cli_core.domain.contracts.load_code_review_contract``; this module
covers the orthogonal concern of mapping a diff feature list to a set of
reviewer roles.
"""

from __future__ import annotations


# Maps feature keywords found in a diff-summary JSON array to the reviewers
# that should be selected when any keyword is present.
REVIEWER_TRIGGER_MAP: dict[str, list[str]] = {
    "auth": ["security-reviewer"],
    "authorization": ["security-reviewer"],
    "api_exposure": ["security-reviewer"],
    "crypto": ["security-reviewer"],
    "encryption": ["security-reviewer"],
    "e2e": ["e2e-reviewer"],
    "ui": ["interaction-reviewer"],
    "frontend": ["interaction-reviewer"],
    "database": ["data-engineer"],
    "migration": ["data-engineer"],
    "architecture": ["architecture-reviewer"],
    "integration": ["integration-impact-expert"],
}

# Reviewers that are always included regardless of diff content.
ALWAYS_ENABLED_REVIEWERS: list[str] = ["correctness-reviewer", "tdd-reviewer"]


def select_reviewers(features: list[str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return ``(selected, excluded)`` reviewer payloads for the given diff features."""
    triggered: set[str] = set()
    for feature in features:
        for keyword, roles in REVIEWER_TRIGGER_MAP.items():
            if keyword in feature:
                triggered.update(roles)

    all_possible = set(ALWAYS_ENABLED_REVIEWERS)
    for roles in REVIEWER_TRIGGER_MAP.values():
        all_possible.update(roles)

    enabled = set(ALWAYS_ENABLED_REVIEWERS) | triggered
    selected = [
        {"role": r, "reason": "always_enabled" if r in ALWAYS_ENABLED_REVIEWERS else "diff_trigger"}
        for r in sorted(enabled)
    ]
    excluded = [
        {"role": r, "reason": "no_trigger"}
        for r in sorted(all_possible - enabled)
    ]
    return selected, excluded
