#!/usr/bin/env python3
"""Generate a target-project project-lint candidate profile.

Bootstrap is intentionally conservative: it writes generated candidates for the
target project, but it does not promote inferred architecture rules to blocking
profile rules.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to bootstrap project-lint") from exc


PROFILE = Path("project-knowledge/engineering/policies/project-lint.yaml")
GENERATED = Path("project-knowledge/engineering/policies/generated/project-lint.generated.yaml")
PACKAGE_SEED = Path("project-knowledge/engineering/policies/project-lint.yaml")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def detect_package_scripts(root: Path) -> dict[str, str]:
    package_json = root / "package.json"
    if not package_json.exists():
        return {}
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts")
    return scripts if isinstance(scripts, dict) else {}


def detect_make_targets(root: Path) -> set[str]:
    makefile = root / "Makefile"
    if not makefile.exists():
        return set()
    text = makefile.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r"^([A-Za-z0-9_.-]+)\s*:", text, flags=re.MULTILINE))


def detect_commands(root: Path) -> dict[str, str]:
    scripts = detect_package_scripts(root)
    commands: dict[str, str] = {}
    script_aliases = {
        "test": ("test", "test:unit", "test:integration", "vitest", "jest"),
        "lint": ("lint", "lint:check", "eslint"),
        "typecheck": ("typecheck", "type-check", "tsc"),
        "build": ("build", "compile"),
    }
    for kind, aliases in script_aliases.items():
        for alias in aliases:
            if alias in scripts:
                commands[kind] = f"npm run {alias}"
                break

    make_targets = detect_make_targets(root)
    for kind in ("test", "lint", "typecheck", "build"):
        if kind not in commands and kind in make_targets:
            commands[kind] = f"make {kind}"

    if "test" not in commands and ((root / "pytest.ini").exists() or (root / "tests").is_dir() or (root / "pyproject.toml").exists()):
        commands["test"] = "python3 -m pytest"
    if (root / "go.mod").exists():
        commands.setdefault("test", "go test ./...")
        commands.setdefault("build", "go build ./...")
    if (root / "Cargo.toml").exists():
        commands.setdefault("test", "cargo test")
        commands.setdefault("build", "cargo build")
    return commands


def detect_source_dirs(root: Path) -> tuple[list[str], list[str]]:
    candidates = ["src", "app", "lib", "packages", "backend", "frontend", "server", "client"]
    source_patterns = [f"{name}/**" for name in candidates if (root / name).is_dir()]
    ignore_patterns = ["docs/**", "harness-runtime/**", ".harness/**", "tests/**", "**/*.md"]
    if not source_patterns:
        source_patterns = ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.go", "**/*.rs"]
    return source_patterns, ignore_patterns


def detect_external_commands(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if any((root / name).exists() for name in (".dependency-cruiser.cjs", ".dependency-cruiser.js", ".dependency-cruiser.json")):
        items.append(
            {
                "id": "ARCH-DEPENDENCY-CRUISER",
                "command": "npx dependency-cruiser src --config .dependency-cruiser.cjs",
                "severity": "FAIL",
                "source": "CONFIRMED",
            }
        )
    if (root / ".semgrep").is_dir() or (root / ".semgrep.yml").exists() or (root / ".semgrep.yaml").exists():
        items.append({"id": "SEC-SEMGREP", "command": "semgrep scan", "severity": "FAIL", "source": "CONFIRMED"})
    if (root / "importlinter.toml").exists() or (root / ".importlinter").exists():
        items.append({"id": "ARCH-IMPORT-LINTER", "command": "lint-imports", "severity": "FAIL", "source": "CONFIRMED"})
    return items


def seed_profile(root: Path, force: bool) -> None:
    target = root / PROFILE
    if target.exists() and not force:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    source_seed = root / PACKAGE_SEED
    if not source_seed.exists():
        script = Path(__file__).resolve()
        candidates = [
            script.parents[4] / "project-knowledge" / "engineering" / "policies" / "project-lint.yaml",
            script.parents[5] / "project-knowledge" / "engineering" / "policies" / "project-lint.yaml",
        ]
        source_seed = next((candidate for candidate in candidates if candidate.exists()), source_seed)
    if source_seed.exists():
        shutil.copyfile(source_seed, target)
    else:
        target.write_text("schema_version: 1\nenabled: true\nmode: blocking\n", encoding="utf-8")


def build_generated(root: Path) -> dict[str, Any]:
    commands = detect_commands(root)
    source_patterns, ignore_patterns = detect_source_dirs(root)
    required = ["test"]
    for optional in ("lint", "typecheck"):
        if optional in commands:
            required.append(optional)
    return {
        "schema_version": 1,
        "generated_at": now(),
        "source": "bootstrap_project_lint",
        "confidence": {
            "commands": "CONFIRMED" if commands else "UNKNOWN",
            "source_patterns": "INFERRED",
            "external_commands": "CONFIRMED",
        },
        "commands": {
            "detected": commands,
            "required_for_code_change_candidate": required,
        },
        "code_change": {
            "patterns_candidate": source_patterns,
            "ignore_patterns_candidate": ignore_patterns,
        },
        "external_commands": {
            "items_candidate": detect_external_commands(root),
        },
        "promotion_note": "Review generated candidates before copying them into project-lint.yaml as blocking project policy.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--force-profile", action="store_true", help="Replace existing project-lint.yaml seed profile")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    seed_profile(root, args.force_profile)
    generated = build_generated(root)
    out = root / GENERATED
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(generated, sort_keys=False, allow_unicode=True), encoding="utf-8")
    payload = {"profile": str(root / PROFILE), "generated": str(out), "commands": generated["commands"]["detected"]}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
