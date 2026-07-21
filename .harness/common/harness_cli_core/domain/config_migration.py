"""harness.yaml 三方迁移（已安装项目升级到新版本模板）。

旧模板基线 / 新模板 / 当前已装三者之间，逐键判定「保留项目现值」还是「采用新模板
值」。归属由 config-ownership.yaml 提供：auto_managed / project_owned，其余皆
framework_owned。本模块是纯函数——不读盘、不写盘，只对 dict 运算，便于单测。

分类（category）：
  auto_managed       元数据，采用上游。
  unchanged          framework，新旧值相同（no-op）。
  adopt_framework    framework，值变了 → 采用上游（diff 展示旧值→新值）。
  new_framework_key  framework，新模板新增 → 采用上游。
  removed_framework  framework，新模板删除 → 丢弃。
  keep_unchanged     project，当前值==上游默认 → 保留（无需决策）。
  keep_customized    project，当前值≠上游默认 → 默认保留，requires_decision。
  new_project_key    project，新模板新增的项目级键 → 默认采用上游默认，requires_decision。
  renamed            当前键在 renames.from 中 → 迁值到 to，requires_decision（确认映射）。
  orphan_project     当前 project 键在新模板里没有归宿 → 默认丢弃，requires_decision。

apply 时以「新模板」为基底深拷贝（保证框架结构整体刷新与新版键序），再把需要保留 /
迁移的项目值覆盖回去。
"""

from __future__ import annotations

import copy
from typing import Any

# 需要用户介入的分类。
DECISION_CATEGORIES = frozenset(
    {"keep_customized", "new_project_key", "renamed", "orphan_project"}
)

# 每类的默认决策动作（无 decisions 时 --accept-defaults 采用）。
DEFAULT_DECISION = {
    "keep_customized": "keep",          # 保留当前值（备选 adopt_default）
    "new_project_key": "adopt_default", # 采用上游默认（备选 set，由用户给值）
    "renamed": "migrate",               # 把旧值迁到新键
    "orphan_project": "drop",           # 丢弃（备选 relocate）
}


def flatten(data: Any, prefix: str = "") -> dict[str, Any]:
    """把嵌套 dict 摊平成 {dot-path: value}。list / 标量 / 空 dict 作为叶子。"""
    out: dict[str, Any] = {}
    if isinstance(data, dict) and data:
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.update(flatten(value, path))
    else:
        out[prefix] = data
    return out


def _matches(path: str, entries: list[str]) -> bool:
    for entry in entries:
        if path == entry or path.startswith(entry + "."):
            return True
    return False


def get_path(data: dict[str, Any], path: str) -> tuple[bool, Any]:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def set_path(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = data
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _ownership(manifest: dict[str, Any]) -> tuple[list[str], list[str], dict[str, str]]:
    project_owned = [str(x) for x in (manifest.get("project_owned") or [])]
    auto_managed = [str(x) for x in (manifest.get("auto_managed") or [])]
    renames: dict[str, str] = {}
    for item in manifest.get("renames") or []:
        if isinstance(item, dict) and item.get("from") and item.get("to"):
            renames[str(item["from"])] = str(item["to"])
    return project_owned, auto_managed, renames


def build_plan(
    current: dict[str, Any],
    upstream: dict[str, Any],
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    """逐键分类，返回有序 todolist 项（每项含 path/category/current/upstream/requires_decision）。"""
    project_owned, auto_managed, renames = _ownership(manifest)
    up_leaves = flatten(upstream)
    cur_leaves = flatten(current)
    items: list[dict[str, Any]] = []

    # pass 1：以新模板叶子为目标 schema。
    for path, up_val in up_leaves.items():
        has_cur = path in cur_leaves
        cur_val = cur_leaves.get(path)
        if _matches(path, auto_managed):
            category = "auto_managed"
        elif _matches(path, project_owned):
            if not has_cur:
                category = "new_project_key"
            elif cur_val == up_val:
                category = "keep_unchanged"
            else:
                category = "keep_customized"
        else:
            if not has_cur:
                category = "new_framework_key"
            elif cur_val == up_val:
                category = "unchanged"
            else:
                category = "adopt_framework"
        items.append(
            {
                "path": path,
                "category": category,
                "current": cur_val if has_cur else None,
                "current_present": has_cur,
                "upstream": up_val,
                "requires_decision": category in DECISION_CATEGORIES,
            }
        )

    # pass 2：当前已装、但新模板里没有的叶子（删除 / 改名）。
    for path, cur_val in cur_leaves.items():
        if path in up_leaves:
            continue
        if path in renames:
            category = "renamed"
            extra = {"rename_to": renames[path]}
        elif _matches(path, project_owned):
            category = "orphan_project"
            extra = {}
        else:
            category = "removed_framework"
            extra = {}
        items.append(
            {
                "path": path,
                "category": category,
                "current": cur_val,
                "current_present": True,
                "upstream": None,
                "requires_decision": category in DECISION_CATEGORIES,
                **extra,
            }
        )
    return items


def summarize(plan: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in plan:
        summary[item["category"]] = summary.get(item["category"], 0) + 1
    summary["requires_decision"] = sum(1 for i in plan if i.get("requires_decision"))
    summary["total"] = len(plan)
    return summary


def apply_plan(
    upstream: dict[str, Any],
    plan: list[dict[str, Any]],
    decisions: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """以新模板为基底，覆盖回需保留 / 迁移的项目值。返回 (merged, applied_actions)。

    decisions：{path: verb}。缺省时用 DEFAULT_DECISION。
    verb 取值：keep / adopt_default（keep_customized、new_project_key）、
              migrate（renamed）、drop / relocate:<path>（orphan_project）。
    """
    decisions = decisions or {}
    merged = copy.deepcopy(upstream)
    applied: list[dict[str, Any]] = []

    for item in plan:
        path = item["path"]
        category = item["category"]
        verb = decisions.get(path) or DEFAULT_DECISION.get(category)

        if category == "keep_unchanged":
            set_path(merged, path, item["current"])
            applied.append({"path": path, "action": "keep", "value": item["current"]})
        elif category == "keep_customized":
            if verb == "adopt_default":
                applied.append({"path": path, "action": "adopt_default", "value": item["upstream"]})
            else:
                set_path(merged, path, item["current"])
                applied.append({"path": path, "action": "keep", "value": item["current"]})
        elif category == "new_project_key":
            if verb and verb.startswith("set:"):
                value = verb[len("set:") :]
                set_path(merged, path, value)
                applied.append({"path": path, "action": "set", "value": value})
            else:
                applied.append({"path": path, "action": "adopt_default", "value": item["upstream"]})
        elif category == "renamed":
            target = item.get("rename_to")
            if verb == "migrate" and target:
                set_path(merged, target, item["current"])
                applied.append({"path": target, "action": "migrate_from", "value": item["current"], "from": path})
            else:
                applied.append({"path": path, "action": "drop", "value": None})
        elif category == "orphan_project":
            if verb and verb.startswith("relocate:"):
                target = verb[len("relocate:") :]
                set_path(merged, target, item["current"])
                applied.append({"path": target, "action": "relocate_from", "value": item["current"], "from": path})
            else:
                applied.append({"path": path, "action": "drop", "value": item["current"]})
        # auto_managed / unchanged / adopt_framework / new_framework_key /
        # removed_framework：基底（新模板）已正确，无需覆盖。

    return merged, applied


def undecided(plan: list[dict[str, Any]], decisions: dict[str, str] | None) -> list[str]:
    """返回仍需决策、却没有显式 decision 的 path（供 migrate 在非 --accept-defaults 时拦截）。"""
    decisions = decisions or {}
    return [item["path"] for item in plan if item.get("requires_decision") and item["path"] not in decisions]
