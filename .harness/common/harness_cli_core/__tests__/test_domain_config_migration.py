"""harness.yaml 三方迁移单测：归属分类 + 合并应用。

覆盖：framework 结构演进被采用、project 值被保留、新模板新增键、键删除、改名迁值、
orphan project 值、decisions 决策分支、undecided 拦截。"""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.config_migration import (  # noqa: E402
    apply_plan,
    build_plan,
    flatten,
    summarize,
    undecided,
)

MANIFEST = {
    "auto_managed": ["harness_template"],
    "project_owned": ["project_name", "brownfield", "e2e.enabled"],
    "renames": [{"from": "old.flag", "to": "new.flag"}],
}


def _category(plan: list[dict], path: str) -> str:
    for item in plan:
        if item["path"] == path:
            return item["category"]
    raise AssertionError(f"path not in plan: {path}")


def test_flatten_treats_list_and_scalar_as_leaf() -> None:
    flat = flatten({"a": {"b": [1, 2], "c": 3}, "d": {}})
    assert flat == {"a.b": [1, 2], "a.c": 3, "d": {}}


def test_framework_value_change_is_adopted() -> None:
    current = {"work_graph": {"lanes": ["old"]}}
    upstream = {"work_graph": {"lanes": ["new"]}}
    plan = build_plan(current, upstream, MANIFEST)
    assert _category(plan, "work_graph.lanes") == "adopt_framework"
    merged, _ = apply_plan(upstream, plan, {})
    assert merged["work_graph"]["lanes"] == ["new"]


def test_project_value_is_kept() -> None:
    current = {"project_name": "myapp", "brownfield": False}
    upstream = {"project_name": "", "brownfield": True}
    plan = build_plan(current, upstream, MANIFEST)
    assert _category(plan, "project_name") == "keep_customized"
    assert _category(plan, "brownfield") == "keep_customized"
    merged, _ = apply_plan(upstream, plan, {})
    assert merged["project_name"] == "myapp"
    assert merged["brownfield"] is False


def test_project_customized_can_adopt_default() -> None:
    current = {"e2e": {"enabled": False}}
    upstream = {"e2e": {"enabled": True}}
    plan = build_plan(current, upstream, MANIFEST)
    merged, applied = apply_plan(upstream, plan, {"e2e.enabled": "adopt_default"})
    assert merged["e2e"]["enabled"] is True
    assert any(a["action"] == "adopt_default" for a in applied)


def test_new_framework_key_is_added() -> None:
    plan = build_plan({}, {"feature": {"x": 1}}, MANIFEST)
    assert _category(plan, "feature.x") == "new_framework_key"
    merged, _ = apply_plan({"feature": {"x": 1}}, plan, {})
    assert merged["feature"]["x"] == 1


def test_new_project_key_defaults_to_upstream() -> None:
    plan = build_plan({}, {"e2e": {"enabled": True}}, MANIFEST)
    assert _category(plan, "e2e.enabled") == "new_project_key"
    merged, _ = apply_plan({"e2e": {"enabled": True}}, plan, {})
    assert merged["e2e"]["enabled"] is True


def test_removed_framework_key_is_dropped() -> None:
    current = {"legacy": {"gone": 1}}
    upstream = {"kept": 2}
    plan = build_plan(current, upstream, MANIFEST)
    assert _category(plan, "legacy.gone") == "removed_framework"
    merged, _ = apply_plan(upstream, plan, {})
    assert "legacy" not in merged


def test_rename_migrates_value() -> None:
    current = {"old": {"flag": "v"}}
    upstream = {"new": {"flag": "default"}}
    plan = build_plan(current, upstream, MANIFEST)
    assert _category(plan, "old.flag") == "renamed"
    merged, applied = apply_plan(upstream, plan, {"old.flag": "migrate"})
    assert merged["new"]["flag"] == "v"
    assert any(a["action"] == "migrate_from" for a in applied)


def test_orphan_project_value_drop_and_relocate() -> None:
    current = {"brownfield": True, "project_name": "x"}
    # brownfield removed from upstream schema, project_name relocated manually
    upstream = {"meta": {}}
    plan = build_plan(current, upstream, MANIFEST)
    assert _category(plan, "brownfield") == "orphan_project"
    merged_drop, _ = apply_plan(upstream, plan, {"brownfield": "drop", "project_name": "drop"})
    assert "brownfield" not in merged_drop
    merged_rel, _ = apply_plan(upstream, plan, {"brownfield": "relocate:meta.brownfield", "project_name": "drop"})
    assert merged_rel["meta"]["brownfield"] is True


def test_undecided_blocks_without_decisions() -> None:
    current = {"project_name": "x"}
    upstream = {"project_name": ""}
    plan = build_plan(current, upstream, MANIFEST)
    # keep_customized requires decision
    assert "project_name" in undecided(plan, {})
    assert undecided(plan, {"project_name": "keep"}) == []


def test_auto_managed_adopts_upstream() -> None:
    current = {"harness_template": {"version": "1.0"}}
    upstream = {"harness_template": {"version": "2.0"}}
    plan = build_plan(current, upstream, MANIFEST)
    assert _category(plan, "harness_template.version") == "auto_managed"
    merged, _ = apply_plan(upstream, plan, {})
    assert merged["harness_template"]["version"] == "2.0"


def test_summary_counts() -> None:
    current = {"project_name": "x", "work_graph": {"lanes": ["a"]}}
    upstream = {"project_name": "", "work_graph": {"lanes": ["b"]}, "newkey": 1}
    plan = build_plan(current, upstream, MANIFEST)
    summary = summarize(plan)
    assert summary["total"] == len(plan)
    assert summary["requires_decision"] >= 1
