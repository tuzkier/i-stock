---
name: visual-interaction-design
description: '当任务涉及 UI、用户旅程、线框图、原型、可视化交互设计或需要把 interaction.md / interaction-spec 转成给人评审的可预览 HTML/SVG 设计变体和 preview 时使用。'
---

# 可视化交互设计

## 目标

把 PRD 阶段产出的产品定义、领域模型、interaction.md 和 interaction-spec/ 中的用户旅程转成可操作、可预览、可归档、可审查的前端原型 / 可视化交互资产。

本技能不依赖外部设计插件。交互专家负责生成和维护 HTML / SVG / CSS 原型资产；Harness 通过 manifest、contract 和 reviewer 管理覆盖、追溯和审查。主可操作原型必须在项目持有的独立原型工程目录持续迭代（`prototype.interactive_prototype.prototype_project_root`，默认建议 `prototype/`，git 跟踪、随 Mission 分支隔离，不在 `project-knowledge/` 下、不在 mission artifact 下），作为唯一默认人类入口，必须尽量还原真实前端页面；说明、状态覆盖、组件清单和 trace 信息只作为内部证据，不默认生成可见页面。AI handoff 仍以 interaction-spec/ 为准。

## 产物

| 产物 | 路径 | 用途 |
|------|------|------|
| 主可操作原型 | 独立原型工程目录（`prototype.interactive_prototype.prototype_project_root`，默认建议 `prototype/`，git 跟踪、随 Mission 分支隔离，不在 `project-knowledge/` 下） | 唯一默认人类入口；面向用户确认的高还原可操作前端页面；不得混入评审说明、AC、trace 或阅读指引 |
| 设计变体 | `harness-runtime/harness/artifacts/<mission-id>/interaction/visual-interaction/variants/` | 归档 HTML / SVG / CSS 设计资产 |
| 内部证据 | `harness-runtime/harness/artifacts/<mission-id>/interaction/visual-interaction/evidence/` | 可选；给 Gate / reviewer 的状态覆盖、截图、说明材料；不作为人类入口 |
| Manifest | `harness-runtime/harness/artifacts/<mission-id>/interaction/visual-interaction/visual-interaction-manifest.json` | 程序化列出变体、来源、hash、覆盖视口和审查状态 |
| 设计 brief | `harness-runtime/harness/artifacts/<mission-id>/interaction/visual-interaction/design-brief.md` | 交互专家生成 HTML / SVG 变体所需的上下文 |
| interaction.md 更新 | `harness-runtime/harness/artifacts/<mission-id>/interaction/interaction.md` | 引用选定变体、用户流程、状态模型和 E2E obligation |

## 集成边界

- Harness 规则负责：上下游追溯、产物归档、manifest、审查 Gate、E2E / screenshot evidence。
- 交互专家负责：基于产品定义、领域模型、interaction-spec 和项目现有风格生成并维护主可操作原型、HTML / SVG / CSS 设计变体和内部证据，并补齐覆盖元数据。
- interaction-reviewer 负责：判断 interaction-spec 和可视化资产是否证明用户路径、状态、错误、权限、键盘 / 焦点和 E2E obligation 设计充分。

## 何时使用

- 任务涉及 `frontend_ui` / `frontend_visual` / `user_journey` / `web_ui`。
- 用户要求“可视化交互设计”“线框图”“原型”“mockup”。
- interaction.md 只有文字，无法支撑前端实现或用户确认。

## 何时不使用

- 纯后端、纯数据、纯 CLI 任务。
- 只需要修改已有文案且没有用户旅程变化。

按 `workflow.md` 执行详细步骤。
#!/usr/bin/env python3
"""Create a manifest for visual interaction design artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SUPPORTED_EXTENSIONS = {".html", ".svg", ".css"}
SIDECAR_SUFFIXES = (".harness.json", ".harness.yaml", ".harness.yml")
HARNESS_COMMENT_RE = re.compile(r"<!--\s*harness:\s*(.*?)\s*-->", re.IGNORECASE | re.DOTALL)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def collect_files(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def sidecar_candidates(path: Path) -> list[Path]:
    return [path.with_name(f"{path.stem}{suffix}") for suffix in SIDECAR_SUFFIXES]


def parse_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[, ]+", value) if item.strip()]
    return [str(value).strip()] if str(value).strip() else []


def parse_comment_metadata(path: Path) -> dict[str, object]:
    if path.suffix.lower() not in {".html", ".svg"}:
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    match = HARNESS_COMMENT_RE.search(text)
    if not match:
        return {}
    metadata: dict[str, object] = {}
    for key, value in re.findall(r"([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*([^\s;]+)", match.group(1)):
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def parse_sidecar_metadata(path: Path) -> dict[str, object]:
    for sidecar in sidecar_candidates(path):
        if not sidecar.exists():
            continue
        try:
            if sidecar.suffix == ".json":
                loaded = json.loads(sidecar.read_text(encoding="utf-8"))
            elif yaml is not None:
                loaded = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
            else:
                loaded = {}
        except (OSError, json.JSONDecodeError):
            loaded = {}
        return loaded if isinstance(loaded, dict) else {}
    return {}


def normalize_metadata(path: Path) -> dict[str, object]:
    metadata = {**parse_comment_metadata(path), **parse_sidecar_metadata(path)}
    covers = metadata.get("covers") if isinstance(metadata.get("covers"), dict) else {}
    flows = parse_list(covers.get("flows") if isinstance(covers, dict) else None) or parse_list(metadata.get("flows"))
    states = parse_list(covers.get("states") if isinstance(covers, dict) else None) or parse_list(metadata.get("states"))
    viewports = (
        parse_list(covers.get("viewports") if isinstance(covers, dict) else None)
        or parse_list(metadata.get("viewports"))
        or ["desktop", "tablet", "mobile"]
    )
    scenarios = parse_list(metadata.get("scenarios"))
    use_cases = (
        parse_list(covers.get("use_cases") if isinstance(covers, dict) else None)
        or parse_list(metadata.get("use_cases"))
    )
    surfaces = parse_list(covers.get("surfaces") if isinstance(covers, dict) else None) or parse_list(metadata.get("surfaces"))
    role = str(metadata.get("role") or metadata.get("artifact_role") or "").strip()
    return {
        "covers": {
            "flows": flows,
            "states": states,
            "viewports": viewports,
            "scenarios": scenarios,
            "use_cases": use_cases,
            "surfaces": surfaces,
        },
        "artifact_role": role,
        "component": metadata.get("component", ""),
        "screen": metadata.get("screen", ""),
        "style_source": metadata.get("style_source", ""),
        "notes": metadata.get("notes", ""),
    }


def copy_files(files: list[Path], source_dir: Path, variants_dir: Path) -> list[Path]:
    copied: list[Path] = []
    variants_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        rel = path.relative_to(source_dir)
        target = variants_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        for sidecar in sidecar_candidates(path):
            if sidecar.exists():
                shutil.copy2(sidecar, target.with_name(sidecar.name))
        copied.append(target)
    return copied


def build_manifest(mission_id: str, stage_dir: Path, files: list[Path], source_dir: Path) -> dict:
    artifacts = []
    for index, path in enumerate(files, start=1):
        stat = path.stat()
        rel_path = path.relative_to(stage_dir) if path.is_relative_to(stage_dir) else path
        metadata = normalize_metadata(path)
        artifacts.append(
            {
                "id": f"VIZ-{index:03d}",
                "path": str(rel_path),
                "absolute_path": str(path.resolve()),
                "type": path.suffix.lower().lstrip("."),
                "size_bytes": stat.st_size,
                "sha256": sha256(path),
                "modified_at": iso_mtime(path),
                "source": str(source_dir),
                "covers": metadata["covers"],
                "artifact_role": metadata["artifact_role"],
                "screen": metadata["screen"],
                "component": metadata["component"],
                "style_source": metadata["style_source"],
                "notes": metadata["notes"],
                "review_status": "pending",
            }
        )
    return {
        "type": "visual_interaction_manifest",
        "version": 1,
        "mission_id": mission_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage_dir": str(stage_dir),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "review_inputs": {
            "interaction_doc": f"harness-runtime/harness/artifacts/{mission_id}/interaction/interaction.md",
            "manifest": "visual-interaction-manifest.json",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--stage-dir", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--copy", action="store_true")
    parser.add_argument("--output", default="visual-interaction-manifest.json")
    args = parser.parse_args()

    stage_dir = Path(args.stage_dir)
    source_dir = Path(args.source_dir)
    variants_dir = stage_dir / "variants"
    stage_dir.mkdir(parents=True, exist_ok=True)

    source_files = collect_files(source_dir)
    files = copy_files(source_files, source_dir, variants_dir) if args.copy else source_files
    manifest = build_manifest(args.mission_id, stage_dir, files, source_dir)

    output_path = stage_dir / args.output
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output_path), "artifact_count": len(files)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
