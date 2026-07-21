from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload, finding, status_from_findings
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.config_migration import (
    apply_plan,
    build_plan,
    summarize,
    undecided,
)
from harness_cli_core.domain.config_snapshot import build_config_snapshot_payload
from harness_cli_core.infra.io import load_yaml, write_yaml
from harness_cli_core.infra.runtime_paths import load_runtime_config


def load_model_routing(root: Path) -> dict:
    model_routing = load_yaml(root / "harness-runtime" / "config" / "model-routing.yaml")
    if not model_routing:
        model_routing = load_yaml(root / "package" / "harness-runtime" / "config" / "model-routing.yaml")
    return model_routing


def cmd_config_snapshot(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    config = load_runtime_config(root)
    if not config:
        return emit_payload(args, fail_payload("config.snapshot", "missing_runtime_config", "Harness runtime config not found"))
    return emit_payload(args, build_config_snapshot_payload(root, config, load_model_routing(root)))


# --- config diff / migrate（已安装项目升级到新版本模板的 yaml 三方迁移）-----------

def _first_existing(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def _resolve_upstream_file(upstream: Path, *rel: str) -> Path | None:
    if upstream.is_file():
        return upstream
    return _first_existing([upstream / r for r in rel])


def _resolve_current_config(root: Path, current_arg: str | None) -> Path | None:
    if current_arg:
        path = Path(current_arg).expanduser()
        return path if path.exists() else None
    return _first_existing([root / "harness-runtime" / "config" / "harness.yaml"])


def _resolve_upstream_config(upstream: Path) -> Path | None:
    return _resolve_upstream_file(
        upstream,
        "harness-runtime/config/harness.yaml",
        "harness-runtime/config/harness.yaml",
    )


def _resolve_ownership(upstream: Path, ownership_arg: str | None, root: Path) -> Path | None:
    if ownership_arg:
        path = Path(ownership_arg).expanduser()
        return path if path.exists() else None
    return _resolve_upstream_file(
        upstream,
        "harness-runtime/config/config-ownership.yaml",
        "harness-runtime/config/config-ownership.yaml",
    ) or _first_existing([root / "harness-runtime" / "config" / "config-ownership.yaml"])


def _load_plan(args: argparse.Namespace, control: str) -> tuple[dict | None, list[dict] | None, dict | None]:
    """解析 current / upstream / ownership 并构建 plan；失败返回 fail payload。"""
    root = Path(root_arg(args))
    upstream = Path(str(getattr(args, "upstream", "") or "")).expanduser()
    if not str(upstream) or not upstream.exists():
        return None, None, fail_payload(control, "missing_upstream", "--upstream 路径不存在；传入新版本 HarnessV2 源码（或对应 harness.yaml）路径")
    up_cfg = _resolve_upstream_config(upstream)
    if not up_cfg:
        return None, None, fail_payload(control, "missing_upstream_config", f"在 {upstream} 下找不到新模板 harness.yaml")
    cur_cfg = _resolve_current_config(root, getattr(args, "current", None))
    if not cur_cfg:
        return None, None, fail_payload(control, "missing_current_config", "找不到当前已装 harness.yaml（--current 或 <root>/harness-runtime/config/harness.yaml）")
    ownership = _resolve_ownership(upstream, getattr(args, "ownership", None), root)
    manifest = load_yaml(ownership) if ownership else {}

    plan = build_plan(load_yaml(cur_cfg), load_yaml(up_cfg), manifest)
    meta = {
        "current_config": str(cur_cfg),
        "upstream_config": str(up_cfg),
        "ownership": str(ownership) if ownership else None,
        "ownership_present": bool(manifest),
    }
    return meta, plan, None


def cmd_config_diff(args: argparse.Namespace) -> int:
    meta, plan, fail = _load_plan(args, "config.diff")
    if fail is not None:
        return emit_payload(args, fail)
    summary = summarize(plan)
    findings: list[dict] = []
    if not meta["ownership_present"]:
        findings.append(finding("WARN", "ownership_manifest_absent", "未找到 config-ownership.yaml，全部键按 framework_owned 处理（升级会采用上游值）"))
    for category in ("orphan_project", "renamed", "keep_customized", "new_project_key"):
        count = summary.get(category, 0)
        if count:
            findings.append(finding("WARN", f"requires_decision.{category}", f"{count} 项需决策（{category}）"))
    payload = {
        "status": status_from_findings(findings),
        "control": "config.diff",
        **meta,
        "summary": summary,
        "plan": plan,
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_config_migrate(args: argparse.Namespace) -> int:
    meta, plan, fail = _load_plan(args, "config.migrate")
    if fail is not None:
        return emit_payload(args, fail)

    decisions: dict[str, str] = {}
    decisions_arg = getattr(args, "decisions", None)
    if decisions_arg:
        decisions_path = Path(decisions_arg).expanduser()
        if not decisions_path.exists():
            return emit_payload(args, fail_payload("config.migrate", "missing_decisions", f"决策文件不存在：{decisions_path}"))
        loaded = load_yaml(decisions_path)
        decisions = {str(k): str(v) for k, v in (loaded.get("decisions") or loaded).items()} if isinstance(loaded, dict) else {}

    accept_defaults = bool(getattr(args, "accept_defaults", False))
    pending = undecided(plan, decisions)
    if pending and not accept_defaults:
        payload = fail_payload(
            "config.migrate",
            "decisions_required",
            f"{len(pending)} 项需决策但未提供（先看 config diff，再用 --decisions 或 --accept-defaults）",
        )
        payload["pending"] = pending
        payload["summary"] = summarize(plan)
        return emit_payload(args, payload)

    merged, applied = apply_plan(load_yaml(Path(meta["upstream_config"])), plan, decisions)

    dry_run = bool(getattr(args, "dry_run", False))
    output_arg = getattr(args, "output", None)
    written: str | None = None
    backup: str | None = None
    if not dry_run:
        target = Path(output_arg).expanduser() if output_arg else Path(meta["current_config"])
        if not output_arg and target.exists():
            backup_path = target.with_suffix(target.suffix + ".bak")
            backup_path.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
            backup = str(backup_path)
        write_yaml(target, merged)
        written = str(target)

    findings = [finding("WARN", "applied_with_defaults", "部分需决策项采用默认决策") if pending else None]
    findings = [f for f in findings if f]
    payload = {
        "status": "PASS",
        "control": "config.migrate",
        **meta,
        "summary": summarize(plan),
        "applied": applied,
        "written": written,
        "backup": backup,
        "dry_run": dry_run,
        "merged": merged if dry_run else None,
        "findings": findings,
    }
    return emit_payload(args, payload)
