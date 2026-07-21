from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_cli_core.infra.io import load_yaml, write_yaml


def load_manifest(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return load_yaml(path)
        return data if isinstance(data, dict) else {}
    return load_yaml(path)


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        write_yaml(path, payload)


def replace_template_values(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        for key, replacement in replacements.items():
            value = value.replace("{{" + key + "}}", replacement)
        return value
    if isinstance(value, list):
        return [replace_template_values(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: replace_template_values(item, replacements) for key, item in value.items()}
    return value
