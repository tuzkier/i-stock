#!/usr/bin/env python3
"""Generate a minimal reviewable patch for mechanical runtime drift findings."""

from __future__ import annotations

import argparse
import difflib
import json
from datetime import datetime, timezone
from pathlib import Path


CONTRACT_SNIPPETS = {
    "mission-contract.md": """## Control Contract

- Contract: `contracts/mission-contract.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

""",
    "product/product-definition.md": """## Control Contract

- Contract: `contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

""",
    "execution-brief.md": """## Control Contract

- Contract: `contracts/execution-brief.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

""",
    "verification-report.md": """## Control Contract

- Contract: `contracts/verification-report.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

""",
}


def patch_missing_contract(root: Path, message: str) -> str:
    rel = message.split(" lacks external Control Contract reference", 1)[0]
    path = root / rel
    snippet = CONTRACT_SNIPPETS.get(path.name)
    if not path.exists() or not snippet:
        return ""
    original = path.read_text(encoding="utf-8").splitlines(keepends=True)
    insert_at = 1 if original else 0
    updated = original[:insert_at] + ["\n"] + snippet.splitlines(keepends=True) + original[insert_at:]
    return "".join(difflib.unified_diff(original, updated, fromfile=str(path), tofile=str(path)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--findings-json", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", default="harness-runtime/harness/state/drift-patches")
    args = parser.parse_args()
    findings = json.loads(Path(args.findings_json).read_text(encoding="utf-8")).get("findings", [])
    root = Path(args.root).resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    patch_path = out_dir / f"{timestamp}.patch"
    readme_path = out_dir / f"{timestamp}.README.md"
    mechanical = []
    non_mechanical = []
    patch_chunks: list[str] = []
    for finding in findings:
        if finding.get("code") in {"missing_path", "missing_contract_template", "workflow_path_drift", "workflow_concept_drift"}:
            mechanical.append(finding)
            if finding.get("code") == "missing_contract_template":
                chunk = patch_missing_contract(root, finding.get("message", ""))
                if chunk:
                    patch_chunks.append(chunk)
        elif finding.get("level") == "FAIL":
            non_mechanical.append(finding)
    patch_path.write_text("\n".join(patch_chunks), encoding="utf-8")
    lines = ["# Drift Patch Review", "", "This generator only emits diffs for explicitly mechanical fixes. It never applies patches directly.", ""]
    lines.append("## Mechanical Candidates")
    for item in mechanical:
        lines.append(f"- `{item.get('code')}`: {item.get('message')}")
    lines.append("")
    lines.append("## Non Mechanical Fixes")
    for item in non_mechanical:
        lines.append(f"- `{item.get('code')}`: {item.get('message')}")
    readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"patch": str(patch_path), "readme": str(readme_path), "mechanical_candidates": len(mechanical), "non_mechanical_fix": len(non_mechanical)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
