"""alignment_handlers 的 self-prefix / PS- trace 行为单测。

聚焦验证：interaction 自产的 PS- id 被算作 self_refs（不触发
BROKEN_UPSTREAM_TRACE 误报）；下游 stage 引用图里不存在的 PS- 不被当作
self_ref，会保留在 current_refs 里走上游校验（为 BROKEN_UPSTREAM_TRACE 铺路）。
"""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.app.commands.alignment_handlers import (  # noqa: E402
    _SELF_PREFIXES_BY_STAGE,
)
from harness_cli_core.domain.interaction import TRACE_REF_RE  # noqa: E402


def _self_refs(stage: str, refs: set[str]) -> set[str]:
    """复刻 cmd_alignment_check 的 self_refs 判定（startswith 任一 self-prefix）。"""
    prefixes = _SELF_PREFIXES_BY_STAGE.get(stage, ())
    return {ref for ref in refs if ref.startswith(prefixes)}


def test_interaction_self_prefixes_include_ps() -> None:
    assert "PS-" in _SELF_PREFIXES_BY_STAGE["interaction"]


def test_interaction_self_produced_ps_is_self_ref() -> None:
    # interaction 自产的真 PS id 被算作 self_ref → 不会进 BROKEN_UPSTREAM_TRACE。
    refs = {"PS-SURF-BOARD-empty", "SURF-BOARD"}
    self_refs = _self_refs("interaction", refs)
    assert "PS-SURF-BOARD-empty" in self_refs
    # current_refs - self_refs 为空，故不报 BROKEN。
    assert (refs - self_refs) == set()


def test_downstream_ps_ref_not_self_and_stays_for_upstream_check() -> None:
    # 下游 stage（solution / tech / breakdown）的 self-prefix 不含 PS-，所以引用
    # 一个图里不存在的 PS- 会保留下来走上游校验（铺路 BROKEN_UPSTREAM_TRACE）。
    refs = {"PS-SURF-BOARD-empty"}
    for stage in ("solution", "technical_analysis", "breakdown"):
        self_refs = _self_refs(stage, refs)
        assert "PS-SURF-BOARD-empty" not in self_refs
        assert (refs - self_refs) == {"PS-SURF-BOARD-empty"}


def test_ps_ref_is_collected_into_current_refs() -> None:
    # PS- 已纳入 TRACE_REF_RE，故下游契约文本里的 PS- 会被 collect 进 current_refs。
    assert "PS-SURF-BOARD-empty" in set(TRACE_REF_RE.findall("traces_to: PS-SURF-BOARD-empty"))
