#!/usr/bin/env python3
"""verify M3.1 PostToolUse hook: mirror ac_trace patch mutations to the
evidence graph (AC → command_evidence and AC → result_evidence edges).

When the agent calls `harness contract patch` or `harness contract
add-execution-result` and the response indicates success, this hook
reads the current verification-report.contract.yaml and rebuilds the
typed AC-command-result three-chain in:
  harness-runtime/harness/stages/<mission>/traces/evidence_graph.json

Format:
  {
    "nodes": [
      {"id": "<ac_id>",  "type": "ac"},
      {"id": "<cmd_id>", "type": "command_evidence"},
      {"id": "<res_id>", "type": "result_evidence"}
    ],
    "edges": [
      {"from": "<ac_id>",  "to": "<cmd_id>", "rel": "commands"},
      {"from": "<ac_id>",  "to": "<res_id>", "rel": "results"}
    ]
  }

Exit convention: 0 = always allow (PostToolUse).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_PATCH_CMD_RE = re.compile(
    r"\bharness\s+contract\s+(?:patch|add-execution-result)\b",
    re.IGNORECASE,
)
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _build_graph(doc: dict) -> dict:
    inner = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: set[str] = set()

    def add_node(nid: str, ntype: str) -> None:
        if nid not in node_ids:
            nodes.append({"id": nid, "type": ntype})
            node_ids.add(nid)

    command_evidence: list[dict] = inner.get("command_evidence") or []
    result_evidence: list[dict] = inner.get("result_evidence") or []
    for ce in command_evidence:
        if isinstance(ce, dict) and ce.get("id"):
            add_node(ce["id"], "command_evidence")
    for re_ in result_evidence:
        if isinstance(re_, dict) and re_.get("id"):
            add_node(re_["id"], "result_evidence")

    ac_traces: list[dict] = inner.get("ac_trace") or []
    for ac in ac_traces:
        if not isinstance(ac, dict):
            continue
        ac_id = ac.get("id") or ac.get("ac_id")
        if not ac_id:
            continue
        add_node(ac_id, "ac")
        for cmd_id in ac.get("command_evidence_ids") or []:
            if isinstance(cmd_id, str):
                add_node(cmd_id, "command_evidence")
                edges.append({"from": ac_id, "to": cmd_id, "rel": "commands"})
        for res_id in ac.get("result_evidence_ids") or []:
            if isinstance(res_id, str):
                add_node(res_id, "result_evidence")
                edges.append({"from": ac_id, "to": res_id, "rel": "results"})

    return {"nodes": nodes, "edges": edges, "built_at": datetime.now(timezone.utc).isoformat()}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not _PATCH_CMD_RE.search(command):
        return 0
    if yaml is None:
        return 0
    mission_match = _MISSION_FLAG_RE.search(command)
    if mission_match is None:
        return 0
    mission_id = mission_match.group(1)
    cwd = Path(payload.get("cwd") or ".")
    contract_path = (
        cwd
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "verification-report.contract.yaml"
    )
    if not contract_path.exists():
        return 0
    try:
        doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return 0
    if not isinstance(doc, dict):
        return 0
    graph = _build_graph(doc)
    traces_dir = (
        cwd / "harness-runtime" / "harness" / "stages" / mission_id / "traces"
    )
    try:
        traces_dir.mkdir(parents=True, exist_ok=True)
        (traces_dir / "evidence_graph.json").write_text(
            json.dumps(graph, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
