"""Unit tests for the trace-coverage (SURF↔SUC↔OBJ) reconciliation logic."""

from __future__ import annotations

import sys
import argparse
import contextlib
import io
import json
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.interaction import (  # noqa: E402
    build_trace_index,
    extract_data_anchor_ids,
    operable_visible_text,
    strip_field_anchored_text,
    trace_coverage_findings,
)


def _codes(findings):
    return {f["code"] for f in findings}


def test_clean_binding_passes_with_no_fail():
    findings = trace_coverage_findings(
        prd_suc={"SUC-01", "SUC-01-OP-01"},
        prd_obj={"OBJ-01"},
        spec_surf={"SURF-001"},
        spec_suc={"SUC-01", "SUC-01-OP-01"},
        spec_obj={"OBJ-01"},
        proto_surf={"SURF-001"},
        proto_suc={"SUC-01-OP-01"},  # OP child counts for base SUC-01
        proto_obj={"OBJ-01"},
    )
    assert all(f["level"] != "FAIL" for f in findings)


def test_unknown_spec_ref_fails():
    findings = trace_coverage_findings(
        prd_suc={"SUC-01"}, prd_obj={"OBJ-01"},
        spec_surf={"SURF-001"}, spec_suc={"SUC-99"}, spec_obj={"OBJ-01"},
        proto_surf={"SURF-001"}, proto_suc={"SUC-99"}, proto_obj={"OBJ-01"},
    )
    assert "TRACE_SPEC_SUC_UNKNOWN" in _codes(findings)


def test_declared_but_not_anchored_fails():
    findings = trace_coverage_findings(
        prd_suc={"SUC-01"}, prd_obj={"OBJ-01", "OBJ-02"},
        spec_surf={"SURF-001"}, spec_suc={"SUC-01"}, spec_obj={"OBJ-01", "OBJ-02"},
        proto_surf={"SURF-001"}, proto_suc={"SUC-01"}, proto_obj={"OBJ-01"},  # OBJ-02 dropped
    )
    assert "TRACE_OBJ_NOT_ANCHORED" in _codes(findings)


def test_dangling_anchor_fails():
    findings = trace_coverage_findings(
        prd_suc={"SUC-01"}, prd_obj={"OBJ-01"},
        spec_surf={"SURF-001"}, spec_suc={"SUC-01"}, spec_obj={"OBJ-01"},
        proto_surf={"SURF-001", "SURF-999"},  # SURF-999 not declared
        proto_suc={"SUC-01"}, proto_obj={"OBJ-01"},
    )
    assert "TRACE_ANCHOR_SURF_DANGLING" in _codes(findings)


def test_unbound_prd_id_warns_not_fails():
    findings = trace_coverage_findings(
        prd_suc={"SUC-01", "SUC-02"}, prd_obj={"OBJ-01"},
        spec_surf={"SURF-001"}, spec_suc={"SUC-01"}, spec_obj={"OBJ-01"},
        proto_surf={"SURF-001"}, proto_suc={"SUC-01"}, proto_obj={"OBJ-01"},
    )
    codes = _codes(findings)
    assert "TRACE_PRD_SUC_UNBOUND" in codes
    warn = [f for f in findings if f["code"] == "TRACE_PRD_SUC_UNBOUND"][0]
    assert warn["level"] == "WARN"


def test_extract_data_anchor_ids():
    html = (
        '<section data-surf="SURF-002" data-suc="SUC-03-OP-01" data-obj="OBJ-01">'
        '<button data-suc="SUC-03-OP-02">x</button></section>'
    )
    anchors = extract_data_anchor_ids(html)
    assert anchors["surf"] == {"SURF-002"}
    assert anchors["obj"] == {"OBJ-01"}
    assert {"SUC-03-OP-01", "SUC-03-OP-02"} <= anchors["suc"]


def test_strip_field_anchored_text_exempts_declared_domain_values():
    html = (
        '<span class="node-id" data-field="OBJ-02.id">REQ-THEFORCE-WORKGRAPH</span>'
        "<p>reviewer note about SCN-01 leaked into prose</p>"
    )
    stripped = strip_field_anchored_text(html)
    # declared domain field value removed (not flagged as spec leakage)...
    assert "REQ-THEFORCE-WORKGRAPH" not in stripped
    # ...but genuine prose leakage is preserved for the forbidden-copy scan to catch
    assert "SCN-01" in stripped


def test_operable_visible_text_excludes_attributes_and_domain_values():
    html = (
        '<div class="node-card" data-testid="node-card-REQ-THEFORCE" '
        "onclick=\"openNode('REQ-THEFORCE')\">"
        '<span class="node-id" data-field="OBJ-02.id">REQ-THEFORCE</span>'
        "</div>"
        "<p>评审入口：reviewer should read SCN-09 first</p>"
    )
    text = operable_visible_text(html)
    # domain id in data-field value + in testid/onclick attributes are all excluded
    assert "REQ-THEFORCE" not in text
    # genuine visible review prose is preserved for the forbidden-copy scan
    assert "评审入口" in text
    assert "SCN-09" in text


def test_build_trace_index_shape():
    idx = build_trace_index(
        mission="M-1", prd_suc={"SUC-01"}, prd_obj={"OBJ-01"},
        spec_surf={"SURF-001"}, spec_suc={"SUC-01"}, spec_obj={"OBJ-01"},
        proto_surf={"SURF-001"}, proto_suc={"SUC-01"}, proto_obj={"OBJ-01"},
        status="PASS",
    )
    assert idx["type"] == "trace_index"
    assert idx["object_axis"] == "OBJ"
    assert idx["prototype_anchors"]["obj"] == ["OBJ-01"]


def test_resolve_feedback_routing(tmp_path):
    from harness_cli_core.domain.interaction import resolve_feedback_routing
    mid = "M-1"
    sd = tmp_path / "harness-runtime" / "harness" / "artifacts" / mid / "interaction" / "interaction-spec"
    sd.mkdir(parents=True)
    (sd / "surface-model.md").write_text("| SURF-002 | x | SUC-03 | OBJ-01 |\n", encoding="utf-8")
    out = resolve_feedback_routing(tmp_path, mid, surface="SURF-002")
    assert out["query"]["surface"] == "SURF-002"
    assert any("surface-model.md" in r["path"] for r in out["spec_references"])
    out_suc = resolve_feedback_routing(tmp_path, mid, suc="SUC-03")
    assert any("use-case-model" in c for c in out_suc["upstream_candidates"])


def test_surface_binding_ids_empty_when_no_contract(tmp_path):
    from harness_cli_core.domain.interaction import interaction_surface_binding_ids
    out = interaction_surface_binding_ids(tmp_path, "M-1")
    assert out == {"surf": set(), "suc": set(), "obj": set()}


def test_surface_binding_ids_parsed_from_contract(tmp_path):
    from harness_cli_core.domain.interaction import interaction_surface_binding_ids
    cd = tmp_path / "harness-runtime" / "harness" / "stages" / "M-1" / "contracts"
    cd.mkdir(parents=True)
    (cd / "interaction.contract.yaml").write_text(
        "prototype:\n  surface_bindings:\n    - surf: SURF-001\n      suc: [SUC-01, SUC-01-OP-01]\n      obj: [OBJ-01]\n",
        encoding="utf-8",
    )
    out = interaction_surface_binding_ids(tmp_path, "M-1")
    assert out["surf"] == {"SURF-001"}
    assert out["obj"] == {"OBJ-01"}
    assert {"SUC-01", "SUC-01-OP-01"} <= out["suc"]


def test_trace_coverage_fails_when_surface_bindings_missing(tmp_path):
    from harness_cli_core.app.commands.interaction_handlers import cmd_interaction_trace_coverage_check

    mid = "M-1"
    visual_dir = tmp_path / "harness-runtime" / "harness" / "artifacts" / mid / "interaction" / "visual-interaction"
    visual_dir.mkdir(parents=True)
    (visual_dir / "prototype").mkdir()
    (visual_dir / "prototype" / "index.html").write_text(
        '<section data-surf="SURF-001">prototype</section>',
        encoding="utf-8",
    )
    (visual_dir / "visual-interaction-manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "path": "prototype/index.html",
                        "type": "html",
                        "role": "operable_prototype",
                        "covers": {"surfaces": ["SURF-001"]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    product_dir = tmp_path / "harness-runtime" / "harness" / "artifacts" / mid / "product"
    product_dir.mkdir(parents=True)
    (product_dir / "use-case-model.md").write_text("SUC-01\n", encoding="utf-8")
    (product_dir / "business-object-analysis.md").write_text("OBJ-01\n", encoding="utf-8")

    args = argparse.Namespace(root=str(tmp_path), global_root=str(tmp_path), mission=mid, prototype_root="", json=True)
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = cmd_interaction_trace_coverage_check(args)

    payload = json.loads(stdout.getvalue())
    assert code == 1
    assert payload["status"] == "FAIL"
    assert any(item["code"] == "TRACE_BINDING_MISSING" for item in payload["findings"])
