"""任务 #7：横切 gap category SSOT 单元测试。

覆盖：常量集合、classify_gap_category 三种返回、未知 category 不被误分类 / 不报错。
"""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.contracts import (  # noqa: E402
    CROSSCUTTING_GAP_CATEGORIES,
    PRODUCER_FIXABLE_GAP_CATEGORIES,
    USER_CLARIFICATION_GAP_CATEGORIES,
    classify_gap_category,
)


# ---------------------------------------------------------------------------
# 常量集合
# ---------------------------------------------------------------------------

def test_crosscutting_set_exact_members() -> None:
    assert CROSSCUTTING_GAP_CATEGORIES == {
        "reasoning_chain_open",
        "internal_contradiction",
        "needs_user_clarification",
    }


def test_semantic_groups_partition_crosscutting() -> None:
    # 两个语义分组合起来恰好覆盖横切全集，且互不重叠。
    assert PRODUCER_FIXABLE_GAP_CATEGORIES == {
        "reasoning_chain_open",
        "internal_contradiction",
    }
    assert USER_CLARIFICATION_GAP_CATEGORIES == {"needs_user_clarification"}
    assert PRODUCER_FIXABLE_GAP_CATEGORIES.isdisjoint(USER_CLARIFICATION_GAP_CATEGORIES)
    assert (
        PRODUCER_FIXABLE_GAP_CATEGORIES | USER_CLARIFICATION_GAP_CATEGORIES
        == CROSSCUTTING_GAP_CATEGORIES
    )


# ---------------------------------------------------------------------------
# classify_gap_category 三种返回
# ---------------------------------------------------------------------------

def test_classify_producer_fixable() -> None:
    assert classify_gap_category("reasoning_chain_open") == "producer_fixable"
    assert classify_gap_category("internal_contradiction") == "producer_fixable"


def test_classify_needs_user_clarification() -> None:
    assert classify_gap_category("needs_user_clarification") == "needs_user_clarification"


def test_classify_stage_specific_for_known_stage_categories() -> None:
    # 既有阶段特有 category 必须归 stage_specific，不能误分类 / 不能报错。
    for category in (
        "lost_business_object",
        "coverage_gap",
        "insufficient_input",
        "missing_invariant",
    ):
        assert classify_gap_category(category) == "stage_specific"


def test_classify_unknown_category_is_stage_specific_no_error() -> None:
    # 完全未知 / 空 / 古怪字符串都兜底为 stage_specific，永不抛错。
    for category in ("", "totally_made_up", "  ", "needs_user_clarification_typo"):
        assert classify_gap_category(category) == "stage_specific"
