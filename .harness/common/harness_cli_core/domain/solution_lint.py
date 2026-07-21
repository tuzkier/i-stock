"""Pure constants for solution stage CLI commands.

The solution lane CLIs (`solution decision-scan`, `solution lane-action-validate`)
consume these phrase / mitigation lists to surface anti-pattern findings.
"""

from __future__ import annotations


# Anti-design / anti-target-driven phrases. Each entry is
# ``(phrase, rule_code, message)`` — surface findings so the AI cannot
# silently ship a solution.md that hides "let's do the simplest thing"
# behind a decision rationale.
SOLUTION_ANTI_PATTERN_PHRASES: tuple[tuple[str, str, str], ...] = (
    ("最小改动", "anti_minimum_change", "Solution must be target-driven, not minimum-change-driven."),
    ("改动最小", "anti_minimum_change", "Solution must be target-driven, not minimum-change-driven."),
    ("minimum change", "anti_minimum_change", "Solution must be target-driven, not minimum-change-driven."),
    ("先做 demo", "anti_demo_first", "Solution must not lead with a demo placeholder."),
    ("先做demo", "anti_demo_first", "Solution must not lead with a demo placeholder."),
    ("demo 先行", "anti_demo_first", "Solution must not lead with a demo placeholder."),
    ("先 demo", "anti_demo_first", "Solution must not lead with a demo placeholder."),
    (
        "临时方案",
        "anti_temporary_plan",
        "Solution must not present a temporary plan as the chosen path; use a decision + tradeoff.",
    ),
    (
        "temporary plan",
        "anti_temporary_plan",
        "Solution must not present a temporary plan as the chosen path; use a decision + tradeoff.",
    ),
    ("临时实现", "anti_temporary_plan", "Solution must not present a temporary plan as the chosen path."),
)


# Vague mitigation phrases that should not appear in risks[].mitigation —
# they betray that the author has not actually mitigated the risk and has
# punted to "think about it later".
SOLUTION_VAGUE_MITIGATION: tuple[str, ...] = (
    "考虑",
    "考虑下",
    "可能",
    "可能要",
    "也许",
    "或许",
    "需要进一步",
    "需要进一步研究",
    "to be determined",
    "TBD",
    "待定",
    "下一步再",
    "later",
)
