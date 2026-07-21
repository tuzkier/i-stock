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
    ac = parse_list(metadata.get("ac") or metadata.get("acceptance_criteria"))
    scenarios = parse_list(metadata.get("scenarios"))
    role = str(metadata.get("role") or metadata.get("artifact_role") or "").strip()
    return {
        "covers": {
            "flows": flows,
            "states": states,
            "viewports": viewports,
            "ac": ac,
            "scenarios": scenarios,
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
            "interaction_doc": f"harness-runtime/harness/stages/{mission_id}/interaction.md",
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
