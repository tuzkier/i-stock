"""Stage hook checks: delivery."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from context import HookContext
from entry import BASH, WRITE, HookEntry
from result import HookResult
from lib import commands, contracts


# --- PreToolUse: contract / artifact guards --------------------------------
_CONTRACT_MARKERS = (
    "delivery-package.contract.yaml",
    "acceptance-result.contract.yaml",
)


def check_contract_via_cli(ctx: HookContext) -> HookResult:
    """Block direct Write/Edit of delivery / acceptance contract YAML."""
    file_path = ctx.file_path or ""
    for marker in _CONTRACT_MARKERS:
        if marker in file_path:
            return HookResult.block(
                "HarnessV2 delivery hook BLOCKED: direct Write/Edit of "
                f"{marker} is forbidden. Use `harness contract fill/patch/"
                "add-verdict --json`."
            )
    return HookResult.ok()


def check_acceptance_write(ctx: HookContext) -> HookResult:
    """Block acceptance-result.md write when delivery contract not initialized
    or verification-report acceptance_trace is malformed."""
    try:
        file_path = ctx.file_path or ""
        if "acceptance-result.md" not in file_path:
            return HookResult.ok()

        contracts_dir = Path(file_path).parent / "contracts"
        delivery_contract = contracts_dir / "delivery.contract.yaml"
        if not delivery_contract.exists():
            return HookResult.block(
                "HarnessV2 delivery hook BLOCKED: delivery.contract.yaml not initialized. "
                "Run `harness contract init --template delivery --mission <id>` first."
            )

        vr_contract = contracts_dir / "verification-report.contract.yaml"
        if vr_contract.exists():
            block = contracts.load_contract(vr_contract)
            acceptance_trace = block.get("acceptance_trace")
            if acceptance_trace is not None and not isinstance(acceptance_trace, list):
                return HookResult.block(
                    "HarnessV2 delivery hook BLOCKED: verification-report.contract.yaml "
                    "has malformed acceptance_trace field. Fix verification-report before delivery."
                )
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


def check_delivery_package_write(ctx: HookContext) -> HookResult:
    """Block delivery-package.md write when contract exists but lacks
    delivery_package.acceptance_state_ref."""
    try:
        file_path = ctx.file_path or ""
        if "delivery-package.md" not in file_path:
            return HookResult.ok()

        contracts_dir = Path(file_path).parent / "contracts"
        delivery_contract = contracts_dir / "delivery.contract.yaml"
        if not delivery_contract.exists():
            # First write before contract init: allow.
            return HookResult.ok()

        block = contracts.load_contract(delivery_contract)
        pkg = block.get("delivery_package")
        if isinstance(pkg, dict) and pkg.get("acceptance_state_ref") is None:
            return HookResult.block(
                "HarnessV2 delivery hook BLOCKED: delivery_package.acceptance_state_ref "
                "is null in delivery.contract.yaml. Set it to the acceptance-result "
                "contract path before writing delivery-package.md."
            )
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


def deny_direct_approval_edit(ctx: HookContext) -> HookResult:
    """Block direct Write/Edit of approvals.json."""
    if "approvals.json" in (ctx.file_path or ""):
        return HookResult.block(
            "HarnessV2 delivery hook BLOCKED: direct Write/Edit of approvals.json is forbidden. "
            "Use `harness approval append --type checkpoint --stage acceptance-result --json`."
        )
    return HookResult.ok()


def deny_direct_mission_status_edit(ctx: HookContext) -> HookResult:
    """Block direct Write/Edit of mission-status.yaml."""
    if "mission-status.yaml" in (ctx.file_path or ""):
        return HookResult.block(
            "HarnessV2 delivery hook BLOCKED: direct Write/Edit of mission-status.yaml "
            "is forbidden in delivery stage. Use `harness mission stage complete "
            "--stage delivery --json` after delivery gate PASS and handoff pause."
        )
    return HookResult.ok()


def deny_direct_workgraph_edit(ctx: HookContext) -> HookResult:
    """Block direct Write/Edit of work-graph/** files."""
    file_path = (ctx.file_path or "").replace("\\", "/")
    if "work-graph/" in file_path:
        return HookResult.block(
            "HarnessV2 delivery hook BLOCKED: direct Write/Edit of work-graph/** "
            "is forbidden. Use `harness graph apply --operation <manifest> --json` "
            "or `harness graph split-node/defer-node/block-node`."
        )
    return HookResult.ok()


def deny_git_danger(ctx: HookContext) -> HookResult:
    """Block dangerous git operations (push / reset --hard / branch -D)."""
    command = ctx.command or ""
    if commands.git_danger(command, kinds=["any-push", "hard-reset", "branch-delete"]):
        return HookResult.block(
            "HarnessV2 delivery hook BLOCKED: dangerous git operation detected: "
            f"{command!r}. Delivery stage prohibits git push, reset --hard, branch -D."
        )
    return HookResult.ok()


def require_handoff_pause(ctx: HookContext) -> HookResult:
    """Block `harness gate advance` unless delivery contract has
    delivery_package.handoff_evidence.pause_required=true."""
    try:
        if not commands.is_advance(ctx.command):
            return HookResult.ok()

        dc_path = _find_delivery_contract(ctx.cwd)
        if dc_path is None:
            # Cannot verify; allow.
            return HookResult.ok()

        block = contracts.load_contract(dc_path)
        pkg = block.get("delivery_package") or {}
        handoff = pkg.get("handoff_evidence") if isinstance(pkg, dict) else None
        handoff = handoff if isinstance(handoff, dict) else {}
        if not handoff.get("pause_required"):
            return HookResult.block(
                "HarnessV2 delivery hook BLOCKED: delivery_package.handoff_evidence."
                "pause_required is not true. Run `harness delivery handoff --pause "
                "--mission <id>` first."
            )
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


def _find_delivery_contract(cwd: Path) -> Path | None:
    """First delivery.contract.yaml under harness-runtime/harness/stages/*/contracts/."""
    base = cwd / "harness-runtime" / "harness" / "stages"
    if not base.is_dir():
        return None
    for path in sorted(base.glob("*/contracts/delivery.contract.yaml")):
        if path.exists():
            return path
    return None


# --- PostToolUse: record sensors -------------------------------------------
def _checksum16(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def mark_acceptance_written(ctx: HookContext) -> HookResult:
    """Record acceptance-result.md path + checksum into delivery contract."""
    try:
        file_path = ctx.file_path or ""
        if "acceptance-result.md" not in file_path:
            return HookResult.ok()
        p = Path(file_path)
        if not p.exists():
            return HookResult.ok()
        checksum = _checksum16(p)
        if checksum is None:
            return HookResult.ok()

        delivery_contract = p.parent / "contracts" / "delivery.contract.yaml"
        if not delivery_contract.exists():
            return HookResult.ok()
        doc = contracts.load_yaml(delivery_contract)
        if doc is None:
            return HookResult.ok()
        block = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
        if not isinstance(block, dict):
            return HookResult.ok()
        pkg = block.get("delivery_package")
        if not isinstance(pkg, dict):
            pkg = {}
            block["delivery_package"] = pkg
        pkg["acceptance_state_ref"] = {
            "path": str(file_path),
            "contract_path": str(delivery_contract),
            "checksum_sha256_prefix": checksum,
        }
        contracts.save_yaml(delivery_contract, doc)
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


def mark_delivery_package_written(ctx: HookContext) -> HookResult:
    """Record delivery-package.md path + checksum into delivery contract."""
    try:
        file_path = ctx.file_path or ""
        if "delivery-package.md" not in file_path:
            return HookResult.ok()
        p = Path(file_path)
        if not p.exists():
            return HookResult.ok()
        checksum = _checksum16(p)
        if checksum is None:
            return HookResult.ok()

        delivery_contract = p.parent / "contracts" / "delivery.contract.yaml"
        if not delivery_contract.exists():
            return HookResult.ok()
        doc = contracts.load_yaml(delivery_contract)
        if doc is None:
            return HookResult.ok()
        block = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
        if not isinstance(block, dict):
            return HookResult.ok()
        pkg = block.get("delivery_package")
        if not isinstance(pkg, dict):
            pkg = {}
            block["delivery_package"] = pkg
        links = pkg.get("evidence_links")
        if not isinstance(links, list):
            links = []
        links = [l for l in links if not (isinstance(l, dict) and l.get("type") == "delivery_package")]
        links.append({
            "type": "delivery_package",
            "path": str(file_path),
            "checksum_sha256_prefix": checksum,
        })
        pkg["evidence_links"] = links
        contracts.save_yaml(delivery_contract, doc)
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


_GRAPH_OP_RE = re.compile(
    r"\bharness\s+graph\s+(apply|split-node|defer-node|block-node|advance-node)\b"
)
_ACCEPTANCE_APPEND_RE = re.compile(
    r"\bharness\s+approval\s+append\b.*--stage\s+acceptance-result\b"
)
_DELIVERY_GATE_RE = re.compile(r"\bharness\s+gate\s+run\b.*--stage\s+delivery\b")


def record_followup_graph_op(ctx: HookContext) -> HookResult:
    """Record split/defer/block/advance graph op events after `harness graph *`."""
    command = ctx.command or ""
    m = _GRAPH_OP_RE.search(command)
    if m:
        event = {
            "event": "followup_graph_op",
            "operation": m.group(1),
            "command": command,
        }
        return HookResult.advise(json.dumps(event))
    return HookResult.ok()


def record_acceptance_checkpoint(ctx: HookContext) -> HookResult:
    """Record acceptance checkpoint approval id/status after `harness approval append`."""
    command = ctx.command or ""
    if not _ACCEPTANCE_APPEND_RE.search(command):
        return HookResult.ok()
    status = commands.status(command) or "unknown"
    event = {
        "event": "acceptance_checkpoint",
        "status": status,
        "command": command,
    }
    return HookResult.advise(json.dumps(event))


def record_delivery_gate(ctx: HookContext) -> HookResult:
    """Record delivery gate run evidence after `harness gate run --stage delivery`."""
    command = ctx.command or ""
    if not _DELIVERY_GATE_RE.search(command):
        return HookResult.ok()
    event = {
        "event": "delivery_gate_run",
        "command": command,
    }
    return HookResult.advise(json.dumps(event))


ENTRIES: list[HookEntry] = [
    HookEntry(id="delivery-check-contract-via-cli", event="PreToolUse", check=check_contract_via_cli, tools=WRITE),
    HookEntry(id="delivery-check-acceptance-write", event="PreToolUse", check=check_acceptance_write, tools=WRITE),
    HookEntry(id="delivery-check-delivery-package-write", event="PreToolUse", check=check_delivery_package_write, tools=WRITE),
    HookEntry(id="delivery-deny-direct-approval-edit", event="PreToolUse", check=deny_direct_approval_edit, tools=WRITE),
    HookEntry(id="delivery-deny-direct-mission-status-edit", event="PreToolUse", check=deny_direct_mission_status_edit, tools=WRITE),
    HookEntry(id="delivery-deny-direct-workgraph-edit", event="PreToolUse", check=deny_direct_workgraph_edit, tools=WRITE),
    HookEntry(id="delivery-deny-git-danger", event="PreToolUse", check=deny_git_danger, tools=BASH),
    HookEntry(id="delivery-require-handoff-pause", event="PreToolUse", check=require_handoff_pause, tools=BASH),
    HookEntry(id="delivery-mark-acceptance-written", event="PostToolUse", check=mark_acceptance_written, tools=WRITE),
    HookEntry(id="delivery-mark-delivery-package-written", event="PostToolUse", check=mark_delivery_package_written, tools=WRITE),
    HookEntry(id="delivery-record-followup-graph-op", event="PostToolUse", check=record_followup_graph_op, tools=BASH),
    HookEntry(id="delivery-record-acceptance-checkpoint", event="PostToolUse", check=record_acceptance_checkpoint, tools=BASH),
    HookEntry(id="delivery-record-delivery-gate", event="PostToolUse", check=record_delivery_gate, tools=BASH),
]
