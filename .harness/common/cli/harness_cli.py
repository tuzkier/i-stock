#!/usr/bin/env python3
"""Harness control-plane CLI.

This first CLI slice is an adapter layer over the existing deterministic
scripts. It gives workflows one stable command surface without changing the
underlying write semantics yet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import yaml


COMMON_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = COMMON_ROOT.parent
SKILLS_ROOT = COMMON_ROOT / "skills"
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))
WORK_GRAPH_SCRIPTS = SKILLS_ROOT / "work-graph" / "scripts"
if str(WORK_GRAPH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))

from harness_cli_core.app.output import (  # noqa: E402
    emit_payload as core_emit_payload,
    fail_payload as core_fail_payload,
    finding as core_finding,
    status_from_findings as core_status_from_findings,
)
from harness_cli_core.app.parser import add_common as core_add_common, root_arg as core_root_arg, with_json as core_with_json  # noqa: E402
from harness_cli_core.app.commands.agent import AgentCommandHandlers, register_agent_commands  # noqa: E402
from harness_cli_core.app.commands.agent_handlers import cmd_agent_dispatch as core_cmd_agent_dispatch  # noqa: E402
from harness_cli_core.app.commands.approval import ApprovalCommandHandlers, register_approval_commands  # noqa: E402
from harness_cli_core.app.commands.approval_handlers import (  # noqa: E402
    cmd_approval_append,
    cmd_approval_latest,
    cmd_approval_require,
)
from harness_cli_core.app.commands.clarification import ClarificationCommandHandlers, register_clarification_commands  # noqa: E402
from harness_cli_core.app.commands.clarification_handlers import (  # noqa: E402
    cmd_clarification_record,
    cmd_clarification_list,
)
from harness_cli_core.app.commands.board import BoardCommandHandlers, register_board_commands  # noqa: E402
from harness_cli_core.app.commands.board_handlers import cmd_board_select  # noqa: E402
from harness_cli_core.app.commands.config import ConfigCommandHandlers, register_config_commands  # noqa: E402
from harness_cli_core.app.commands.config_handlers import cmd_config_diff, cmd_config_migrate, cmd_config_snapshot  # noqa: E402
from harness_cli_core.app.commands.contract import ContractCommandHandlers, register_contract_commands  # noqa: E402
from harness_cli_core.app.commands import contract_handlers as core_contract_handlers  # noqa: E402
from harness_cli_core.app.commands.control import ControlCommandHandlers, register_control_commands  # noqa: E402
from harness_cli_core.app.commands.control_handlers import (  # noqa: E402
    cmd_control_candidates,
    cmd_control_context_index,
    cmd_control_frame,
    cmd_control_guidance,
    cmd_control_status,
)
from harness_cli_core.app.commands.context import ContextCommandHandlers, register_context_commands  # noqa: E402
from harness_cli_core.app.commands.context_handlers import (
    cmd_context_check,
    cmd_context_init,
    project_context_path as core_project_context_path,
    project_context_template_path as core_project_context_template_path,
)  # noqa: E402
from harness_cli_core.app.commands.execution_brief import ExecutionBriefCommandHandlers, register_execution_brief_commands  # noqa: E402
from harness_cli_core.app.commands import execution_brief_handlers as core_execution_brief_handlers  # noqa: E402
from harness_cli_core.app.commands.execute import ExecuteCommandHandlers, register_execute_commands  # noqa: E402
from harness_cli_core.app.commands import execute_handlers as core_execute_handlers  # noqa: E402
from harness_cli_core.app.commands.frame import FrameCommandHandlers, register_frame_commands  # noqa: E402
from harness_cli_core.app.commands.frame_handlers import cmd_frame_current, cmd_frame_explain  # noqa: E402
from harness_cli_core.app.commands.graph import GraphCommandHandlers, register_graph_commands  # noqa: E402
from harness_cli_core.app.commands.graph_handlers import (  # noqa: E402
    cmd_graph_apply,
    cmd_graph_check,
    cmd_graph_node_create,
    cmd_graph_node_show,
    cmd_graph_plan,
    cmd_graph_rebuild,
)
from harness_cli_core.app.commands.knowledge import KnowledgeCommandHandlers, register_knowledge_commands  # noqa: E402
from harness_cli_core.app.commands.knowledge_handlers import (  # noqa: E402
    cmd_knowledge_check,
    cmd_knowledge_index,
    cmd_knowledge_init,
    cmd_knowledge_promote,
    cmd_knowledge_resolve,
)
from harness_cli_core.app.commands.lint import LintCommandHandlers, register_lint_commands  # noqa: E402
from harness_cli_core.app.commands.lint_handlers import (  # noqa: E402
    cmd_lint_graph,
    cmd_lint_project,
    cmd_lint_runtime,
)
from harness_cli_core.app.commands.mission import MissionCommandHandlers, register_mission_commands  # noqa: E402
from harness_cli_core.app.commands import mission_handlers as core_mission_handlers  # noqa: E402
from harness_cli_core.app.commands.delivery import DeliveryCommandHandlers, register_delivery_commands  # noqa: E402
from harness_cli_core.app.commands.delivery_handlers import (  # noqa: E402
    cmd_delivery_agent_capability_status as core_cmd_delivery_agent_capability_status,
    cmd_delivery_check_followups as core_cmd_delivery_check_followups,
    cmd_delivery_compute_conclusion as core_cmd_delivery_compute_conclusion,
    cmd_delivery_compute_follow_ups as core_cmd_delivery_compute_follow_ups,
    cmd_delivery_handoff as core_cmd_delivery_handoff,
    cmd_delivery_summarize as core_cmd_delivery_summarize,
)
from harness_cli_core.app.commands.finishing_branch import (  # noqa: E402
    FinishingBranchCommandHandlers,
    register_finishing_branch_commands,
)
from harness_cli_core.app.commands.finishing_branch_handlers import (  # noqa: E402
    cmd_finishing_branch_cleanup as core_cmd_finishing_branch_cleanup,
    cmd_finishing_branch_detect_test_cmd as core_cmd_finishing_branch_detect_test_cmd,
    cmd_finishing_branch_execute as core_cmd_finishing_branch_execute,
    cmd_finishing_branch_options as core_cmd_finishing_branch_options,
    cmd_finishing_branch_pr_body as core_cmd_finishing_branch_pr_body,
    cmd_finishing_branch_readiness as core_cmd_finishing_branch_readiness,
    cmd_finishing_branch_run_tests as core_cmd_finishing_branch_run_tests,
    cmd_finishing_branch_status as core_cmd_finishing_branch_status,
)
from harness_cli_core.domain.contracts import (  # noqa: E402
    load_control_contract as _load_control_contract,
)
from harness_cli_core.domain.delivery import (  # noqa: E402
    delivery_contract_path as _delivery_contract_path,
)
from harness_cli_core.domain.finishing_branch import (  # noqa: E402
    load_contract as _fb_load_contract,
    mission_info as _fb_mission_info,
    stage_dir as _fb_stage_dir,
)
from harness_cli_core.domain.verification import (  # noqa: E402
    verify_report_path as _verification_report_path,
)
from harness_cli_core.app.commands.gate import GateCommandHandlers, register_gate_commands  # noqa: E402
from harness_cli_core.app.commands.gate_handlers import (  # noqa: E402
    cmd_gate_advance as core_cmd_gate_advance,
    cmd_gate_control_reports as core_cmd_gate_control_reports,
    cmd_gate_report_render as core_cmd_gate_report_render,
    cmd_gate_run as core_cmd_gate_run,
    cmd_gate_transition as core_cmd_gate_transition,
)
from harness_cli_core.app.commands.evidence import EvidenceCommandHandlers, register_evidence_commands  # noqa: E402
from harness_cli_core.app.commands.evidence_handlers import (  # noqa: E402
    cmd_evidence_add as core_cmd_evidence_add,
    cmd_evidence_command_collect as core_cmd_evidence_command_collect,
    cmd_evidence_graph_build as core_cmd_evidence_graph_build,
    cmd_evidence_graph_check as core_cmd_evidence_graph_check,
    cmd_evidence_link as core_cmd_evidence_link,
    cmd_evidence_visual_manifest as core_cmd_evidence_visual_manifest,
)
from harness_cli_core.domain.evidence import (  # noqa: E402
    evidence_store_path as core_evidence_store_path,
    load_evidence_store as core_load_evidence_store,
)
from harness_cli_core.app.commands.retrospective import (  # noqa: E402
    AgentEvalCommandHandlers,
    HarnessGapCommandHandlers,
    ProjectContextCommandHandlers,
    RetrospectiveCommandHandlers,
    register_agent_eval_commands,
    register_harness_gap_commands,
    register_project_context_commands,
    register_retrospective_commands,
)
from harness_cli_core.app.commands.retrospective_handlers import (  # noqa: E402
    cmd_agent_eval_drift as core_cmd_agent_eval_drift,
    cmd_harness_gap_pattern_scan as core_cmd_harness_gap_pattern_scan,
    cmd_mission_artifacts as core_cmd_mission_artifacts,
    cmd_mission_retrospective_data as core_cmd_mission_retrospective_data,
    cmd_project_context_add_lesson as core_cmd_project_context_add_lesson,
    cmd_project_context_drift_scan as core_cmd_project_context_drift_scan,
    cmd_project_context_lint as core_cmd_project_context_lint,
    cmd_retrospective_harness_gap_emit as core_cmd_retrospective_harness_gap_emit,
    cmd_retrospective_harness_gap_init as core_cmd_retrospective_harness_gap_init,
)
from harness_cli_core.app.commands.review import ReviewCommandHandlers, register_review_commands  # noqa: E402
from harness_cli_core.app.commands.verify import VerifyCommandHandlers, register_verify_commands  # noqa: E402
from harness_cli_core.app.commands.verify_handlers import (  # noqa: E402
    cmd_verify_agent_eval_status as core_cmd_verify_agent_eval_status,
    cmd_verify_compute_conclusion as core_cmd_verify_compute_conclusion,
    cmd_verify_compute_scope as core_cmd_verify_compute_scope,
    cmd_verify_detect_contradictions as core_cmd_verify_detect_contradictions,
    cmd_verify_dispatch_reviewer as core_cmd_verify_dispatch_reviewer,
    cmd_verify_dispatch_worker as core_cmd_verify_dispatch_worker,
    cmd_verify_e2e_status as core_cmd_verify_e2e_status,
    cmd_verify_failure_path as core_cmd_verify_failure_path,
    cmd_verify_gate_run as core_cmd_verify_gate_run,
    cmd_verify_prototype_alignment_check as core_cmd_verify_prototype_alignment_check,
    cmd_verify_run_tests as core_cmd_verify_run_tests,
    cmd_verify_true_e2e_check as core_cmd_verify_true_e2e_check,
)
from harness_cli_core.domain.findings import (  # noqa: E402
    apply_compat_warning as _apply_compat_warning,
    finding as _finding,
)
from harness_cli_core.domain.verification import (  # noqa: E402
    BROWSER_PRIMARY_EVIDENCE_KINDS as _BROWSER_PRIMARY_EVIDENCE_KINDS,
    NON_UI_PRIMARY_EVIDENCE_KINDS as _NON_UI_PRIMARY_EVIDENCE_KINDS,
    evidence_role as _evidence_role,
    is_ui_acceptance_trace as _is_ui_acceptance_trace,
    resolve_execution_brief_for_verify as _resolve_execution_brief_for_verify,
    resolve_verify_contract as _resolve_verify_contract,
    verify_report_path as _verify_report_path,
)
from harness_cli_core.app.commands.review_handlers import (  # noqa: E402
    cmd_review_check_ready as core_cmd_review_check_ready,
    cmd_review_e2e_status as core_cmd_review_e2e_status,
    cmd_review_select_reviewers as core_cmd_review_select_reviewers,
    cmd_review_snapshot_diff as core_cmd_review_snapshot_diff,
    cmd_review_toolchain_status as core_cmd_review_toolchain_status,
)
from harness_cli_core.domain.code_review import (  # noqa: E402
    ALWAYS_ENABLED_REVIEWERS as _ALWAYS_ENABLED_REVIEWERS,
    REVIEWER_TRIGGER_MAP as _REVIEWER_TRIGGER_MAP,
)
from harness_cli_core.domain.contracts import (  # noqa: E402
    load_code_review_contract as _resolve_code_review_contract,
)
from harness_cli_core.app.commands.run import RunCommandHandlers, register_run_commands  # noqa: E402
from harness_cli_core.app.commands.run_handlers import (  # noqa: E402
    cmd_run_cancel as core_cmd_run_cancel,
    cmd_run_retry as core_cmd_run_retry,
)
from harness_cli_core.app.commands.acceptance import AcceptanceCommandHandlers, register_acceptance_commands  # noqa: E402
from harness_cli_core.app.commands.acceptance_handlers import (  # noqa: E402
    ACCEPTANCE_DECISION_CLOSED_SET as _ACCEPTANCE_DECISION_CLOSED_SET,
    ACCEPTANCE_EXIT_EVIDENCE_GAP as _ACCEPTANCE_EXIT_EVIDENCE_GAP,
    cmd_acceptance_record as core_cmd_acceptance_record,
)
from harness_cli_core.app.commands.artifact_handlers import (  # noqa: E402
    ARTIFACT_KIND_CLOSED_SET as _ARTIFACT_KIND_CLOSED_SET,
    cmd_mission_artifacts_append as core_cmd_mission_artifacts_append,
)
from harness_cli_core.app.commands.alignment import (  # noqa: E402
    AlignmentCommandHandlers,
    register_alignment_commands,
)
from harness_cli_core.app.commands.alignment_handlers import (  # noqa: E402
    cmd_alignment_check as core_cmd_alignment_check,
)
from harness_cli_core.app.commands.interaction import (  # noqa: E402
    InteractionCommandHandlers,
    register_interaction_commands,
)
from harness_cli_core.app.commands.interaction_handlers import (  # noqa: E402
    cmd_interaction_check_ui_trigger as core_cmd_interaction_check_ui_trigger,
    cmd_interaction_feedback_sync_check as core_cmd_interaction_feedback_sync_check,
    cmd_interaction_gate_run as core_cmd_interaction_gate_run,
    cmd_interaction_locator_check as core_cmd_interaction_locator_check,
    cmd_interaction_spec_check as core_cmd_interaction_spec_check,
    cmd_interaction_ux_quality_check as core_cmd_interaction_ux_quality_check,
    cmd_interaction_visual_coverage_check as core_cmd_interaction_visual_coverage_check,
    cmd_interaction_trace_coverage_check as core_cmd_interaction_trace_coverage_check,
    cmd_interaction_prototype_check as core_cmd_interaction_prototype_check,
    cmd_interaction_project as core_cmd_interaction_project,
    cmd_interaction_resolve_feedback as core_cmd_interaction_resolve_feedback,
)
from harness_cli_core.app.commands.prototype_as_frontend import (  # noqa: E402
    PrototypeAsFrontendCommandHandlers,
    register_prototype_as_frontend_commands,
)
from harness_cli_core.app.commands.prototype_as_frontend_handlers import (  # noqa: E402
    cmd_prototype_as_frontend_changeset_check as core_cmd_prototype_as_frontend_changeset_check,
    cmd_prototype_as_frontend_drift_check as core_cmd_prototype_as_frontend_drift_check,
    cmd_prototype_as_frontend_gate_run as core_cmd_prototype_as_frontend_gate_run,
    cmd_prototype_as_frontend_path_check as core_cmd_prototype_as_frontend_path_check,
)
from harness_cli_core.app.commands.tech_design import (  # noqa: E402
    TechDesignCommandHandlers,
    register_tech_design_commands,
)
from harness_cli_core.app.commands.tech_design_handlers import (  # noqa: E402
    cmd_tech_design_check_capability_trigger as core_cmd_tech_design_check_capability_trigger,
    cmd_tech_design_check_dep_impact_trigger as core_cmd_tech_design_check_dep_impact_trigger,
)
from harness_cli_core.app.commands.discovery import (  # noqa: E402
    DiscoveryCommandHandlers,
    GraphifyCommandHandlers,
    register_discovery_commands,
    register_graphify_commands,
)
from harness_cli_core.app.commands.discovery_handlers import (  # noqa: E402
    cmd_discovery_agent_eng_eval as core_cmd_discovery_agent_eng_eval,
    cmd_discovery_check_dependency_trigger as core_cmd_discovery_check_dependency_trigger,
    cmd_discovery_skip as core_cmd_discovery_skip,
    cmd_discovery_summary as core_cmd_discovery_summary,
    cmd_graphify_status as core_cmd_graphify_status,
)
from harness_cli_core.app.commands.solution import (  # noqa: E402
    SolutionCommandHandlers,
    register_solution_commands,
)
from harness_cli_core.app.commands.solution_handlers import (  # noqa: E402
    cmd_solution_decision_scan as core_cmd_solution_decision_scan,
    cmd_solution_lane_action_validate as core_cmd_solution_lane_action_validate,
)
from harness_cli_core.app.commands.prd import PrdCommandHandlers, register_prd_commands  # noqa: E402
from harness_cli_core.app.commands.prd_handlers import (  # noqa: E402
    cmd_prd_agent_cap_eval as core_cmd_prd_agent_cap_eval,
    cmd_prd_anti_pattern_scan as core_cmd_prd_anti_pattern_scan,
    cmd_prd_domain_model_lint as core_cmd_prd_domain_model_lint,
)
from harness_cli_core.app.commands.spec import SpecCommandHandlers, register_spec_commands  # noqa: E402
from harness_cli_core.app.commands.spec_handlers import (  # noqa: E402
    cmd_spec_check,
    cmd_spec_delta_lint as core_cmd_spec_delta_lint,
    cmd_spec_diff_list as core_cmd_spec_diff_list,
    cmd_spec_init,
    cmd_spec_scan as core_cmd_spec_scan,
    cmd_spec_scan_capabilities as core_cmd_spec_scan_capabilities,
    cmd_spec_scan_from_prd as core_cmd_spec_scan_from_prd,
)
from harness_cli_core.app.commands.todo import TodoCommandHandlers, register_todo_commands  # noqa: E402
from harness_cli_core.app.commands import todo_handlers as core_todo_handlers  # noqa: E402
from harness_cli_core.app.commands.trace import TraceCommandHandlers, register_trace_commands  # noqa: E402
from harness_cli_core.app.commands import trace_handlers as core_trace_handlers  # noqa: E402
from harness_cli_core.app.commands.writing_plans import WritingPlansCommandHandlers, register_writing_plans_commands  # noqa: E402
from harness_cli_core.app.commands import writing_plans_handlers as core_writing_plans_handlers  # noqa: E402
from harness_cli_core.domain.autonomy import (  # noqa: E402
    AUTONOMY_CANONICAL_LEVELS,
    AUTONOMY_LEGACY_ALIASES,
    autonomy_alias_map as core_autonomy_alias_map,
    normalize_autonomy_level as core_normalize_autonomy_level,
    reject_legacy_autonomy_level as core_reject_legacy_autonomy_level,
)
from harness_cli_core.domain.collections import unique as core_unique  # noqa: E402
from harness_cli_core.domain.config_snapshot import (  # noqa: E402
    add_role_model_policy as core_add_role_model_policy,
    detect_model_adapter as core_detect_model_adapter,
    load_project_stage_rules as core_load_project_stage_rules,
    model_policy_defaults as core_model_policy_defaults,
    professional_role_model_policies as core_professional_role_model_policies,
    resolve_role_model_policy as core_resolve_role_model_policy,
    snapshot_execution_governance as core_snapshot_execution_governance,
    snapshot_prototype_config as core_snapshot_prototype_config,
)
from harness_cli_core.domain.contracts import (  # noqa: E402
    CONTRACT_PLACEHOLDER_RE as CORE_CONTRACT_PLACEHOLDER_RE,
    contract_contains_placeholder as core_contract_contains_placeholder,
    contract_governance_conflict as core_contract_governance_conflict,
    contract_hygiene_payload as core_contract_hygiene_payload,
    contract_leaf_values as core_contract_leaf_values,
    contract_template_path as core_contract_template_path,
    control_contract_document as core_control_contract_document,
    scrub_template_role_verdicts as core_scrub_template_role_verdicts,
    set_path_value as core_set_path_value,
    template_prefilled_role_verdict as core_template_prefilled_role_verdict,
    upsert_by_id as core_upsert_by_id,
)
from harness_cli_core.domain.breakdown import resolve_execution_brief_contract as core_resolve_execution_brief_contract  # noqa: E402
from harness_cli_core.domain.execute import translate_execution_brief_to_overlay as core_translate_execution_brief_to_overlay  # noqa: E402
from harness_cli_core.domain.graph_operations import (  # noqa: E402
    graph_operation_input_nodes as core_graph_operation_input_nodes,
    graph_operation_output_nodes as core_graph_operation_output_nodes,
    operation_type_tree as core_operation_type_tree,
    validate_graph_operation_structure as core_validate_graph_operation_structure,
)
from harness_cli_core.domain.knowledge import (  # noqa: E402
    KNOWLEDGE_STAGE_DOMAINS,
    PROJECT_KNOWLEDGE_REQUIRED_PATHS,
    behavior_specs_root as core_behavior_specs_root,
    behavior_specs_template_root as core_behavior_specs_template_root,
    copy_tree_missing as core_copy_tree_missing,
    knowledge_domain as core_knowledge_domain,
    knowledge_frontmatter as core_knowledge_frontmatter,
    knowledge_index_rows as core_knowledge_index_rows,
    knowledge_markdown_files as core_knowledge_markdown_files,
    knowledge_promotion_candidates as core_knowledge_promotion_candidates,
    knowledge_title as core_knowledge_title,
    project_knowledge_root as core_project_knowledge_root,
    project_knowledge_template_root as core_project_knowledge_template_root,
    render_knowledge_index as core_render_knowledge_index,
)
from harness_cli_core.domain.manifest import (  # noqa: E402
    load_manifest as core_load_manifest,
    replace_template_values as core_replace_template_values,
    write_manifest as core_write_manifest,
)
from harness_cli_core.domain.control_state import (  # noqa: E402
    control_nodes_by_id as core_control_nodes_by_id,
    load_control_nodes as core_load_control_nodes,
    load_control_slice as core_load_control_slice,
    mission_slice_from_lane as core_mission_slice_from_lane,
    mission_slice_lane_consistency_findings as core_mission_slice_lane_consistency_findings,
    mission_slice_primary_nodes as core_mission_slice_primary_nodes,
    mission_summary as core_mission_summary,
    node_summary as core_node_summary,
)
from harness_cli_core.domain.control_status import (  # noqa: E402
    active_mission_ids as core_active_mission_ids,
    approved_checkpoints_for_mission as core_approved_checkpoints_for_mission,
    checkpoint_names as core_checkpoint_names,
    collect_control_status as core_collect_control_status,
    collect_required_approvals as core_collect_required_approvals,
    control_active_slice_ids as core_control_active_slice_ids,
    gate_report_paths as core_gate_report_paths,
    load_control_approval_records as core_load_control_approval_records,
    load_control_gate_reports as core_load_control_gate_reports,
    mission_entry_operation_completed as core_mission_entry_operation_completed,
    normalize_checkpoint as core_normalize_checkpoint,
    open_mission_ids as core_open_mission_ids,
)
from harness_cli_core.domain.control_candidates import (  # noqa: E402
    build_continue_candidates as core_build_continue_candidates,
    node_status_by_id as core_node_status_by_id,
)
from harness_cli_core.domain.control_context import (  # noqa: E402
    build_context_index as core_build_context_index,
    control_relpath as core_control_relpath,
    path_item as core_path_item,
    selected_mission_slice as core_selected_mission_slice,
)
from harness_cli_core.domain.control_frame import (  # noqa: E402
    build_control_frame as core_build_control_frame,
    latest_gate_report_for_mission as core_latest_gate_report_for_mission,
    load_advance_after_gate_module as core_load_advance_after_gate_module,
    next_graph_operation_for_frame as core_next_graph_operation_for_frame,
)
from harness_cli_core.domain.control_guidance import (  # noqa: E402
    GUIDANCE_CATEGORIES as CORE_GUIDANCE_CATEGORIES,
    blocked_guidance_payload as core_blocked_guidance_payload,
    build_control_guidance as core_build_control_guidance,
    entered_stage_obligations_payload as core_entered_stage_obligations_payload,
    guidance_required_controls as core_guidance_required_controls,
    missing_review_evidence as core_missing_review_evidence,
    stage_participation_policy_payload as core_stage_participation_policy_payload,
)
from harness_cli_core.domain.frame import (  # noqa: E402
    build_lane_action_payload as core_build_lane_action_payload,
    load_mission_slice as core_load_mission_slice,
    mission_slice_path as core_mission_slice_path,
)
from harness_cli_core.domain.approvals import (  # noqa: E402
    approval_matches as core_approval_matches,
    approval_stage_completion_status as core_approval_stage_completion_status,
    approvals_path as core_approvals_path,
    checkpoint_name as core_checkpoint_name,
    load_approvals as core_load_approvals,
    mission_stage_completion_status as core_mission_stage_completion_status,
    next_approval_id as core_next_approval_id,
    stage_completion_config as core_stage_completion_config,
    sync_checkpoint_passed as core_sync_checkpoint_passed,
    write_approvals as core_write_approvals,
)
from harness_cli_core.infra.io import load_yaml as core_load_yaml, write_yaml as core_write_yaml  # noqa: E402
from harness_cli_core.infra.process import run_python as core_run_python, run_python_capture as core_run_python_capture  # noqa: E402
from harness_cli_core.infra.runtime_paths import (  # noqa: E402
    load_runtime_config as core_load_runtime_config,
    mission_status_path as core_mission_status_path,
    relpath as core_relpath,
    resolve_path as core_resolve_path,
    runtime_harness_root as core_runtime_harness_root,
    work_graph_root as core_work_graph_root,
)
from harness_cli_core.infra.runtime_layout import (  # noqa: E402
    control_common_root as core_control_common_root,
    control_graph_root as core_control_graph_root,
    control_runtime_root as core_control_runtime_root,
    control_status_path as core_control_status_path,
    explicit_runtime_config_path as core_explicit_runtime_config_path,
    resolve_runtime_layout as core_resolve_runtime_layout,
)
from harness_cli_core.infra.time import now_iso as core_now_iso, today as core_today  # noqa: E402
from work_graph_lib import (  # noqa: E402
    Finding as WGFinding,
    lane_of_stage as wg_lane_of_stage,
    lane_action_registry as wg_lane_action_registry,
    lane_action_snapshot as wg_lane_action_snapshot,
    load_nodes as wg_load_nodes,
    resolve_graph_root as wg_resolve_graph_root,
    lane_stage_for_node as wg_lane_stage_for_node,
    write_views as wg_write_views,
    validate_graph_operation_structure as wg_validate_graph_operation_structure,
    validate_operation_against_profile as wg_validate_operation_against_profile,
)

CLOSED_MISSION_STATUSES = {"done", "closed", "cancelled", "delivered"}


def script(*parts: str) -> Path:
    return SKILLS_ROOT.joinpath(*parts)


def add_common(parser: argparse.ArgumentParser, *, json_default: bool = False) -> None:
    return core_add_common(parser, json_default=json_default)


def root_arg(args: argparse.Namespace) -> str:
    return core_root_arg(args)


def run_python(path: Path, forwarded: list[str], *, cwd: str | None = None) -> int:
    return core_run_python(path, forwarded, cwd=cwd)


def run_python_capture(path: Path, forwarded: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return core_run_python_capture(path, forwarded, cwd=cwd)


def with_json(args: argparse.Namespace, forwarded: list[str]) -> list[str]:
    return core_with_json(args, forwarded)


def load_yaml(path: Path) -> dict[str, Any]:
    return core_load_yaml(path)


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    return core_write_yaml(path, payload)


def today() -> str:
    return core_today()


def now_iso() -> str:
    return core_now_iso()


def runtime_harness_root(root: Path) -> Path:
    """Resolve runtime root, preferring installed-project layout but falling back to
    the source-repo layout (harness-runtime/harness) so commands work in
    both environments without requiring callers to know which layout is in use.

    This is the only acceptable form of path fallback: it is deterministic, observable
    via the returned path, and never silently masks "missing runtime" — that is FAILed
    by load_runtime_config / individual command preconditions.
    """
    return core_runtime_harness_root(root)


def work_graph_root(root: Path) -> Path:
    return core_work_graph_root(root)


def mission_status_path(root: Path) -> Path:
    return core_mission_status_path(root)


def relpath(root: Path, path: Path) -> str:
    return core_relpath(root, path)


def resolve_path(root: Path, value: str | None) -> Path | None:
    return core_resolve_path(root, value)


def load_runtime_config(root: Path) -> dict[str, Any]:
    return core_load_runtime_config(root)


def load_project_stage_rules(root: Path) -> tuple[dict[str, Any], Path | None]:
    return core_load_project_stage_rules(root)


def snapshot_prototype_config(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    return core_snapshot_prototype_config(root, config)


# --- Autonomy level normalization (intake-improvement-plan M1.4) -----------
# Canonical autonomy levels (Chinese, matching harness.yaml execution_governance
# definitions). Legacy aliases (A1/A2/A3 and the English autonomous_* names)
# are normalized on read paths (config.snapshot) and rejected on write paths
# (mission init / contract YAML) with a typed LEGACY_LEVEL_REJECTED finding.

def autonomy_alias_map(config: dict[str, Any]) -> dict[str, str]:
    return core_autonomy_alias_map(config)


def normalize_autonomy_level(value: Any, aliases: dict[str, str]) -> str | None:
    return core_normalize_autonomy_level(value, aliases)


def reject_legacy_autonomy_level(
    control: str, value: Any, aliases: dict[str, str]
) -> dict[str, Any] | None:
    return core_reject_legacy_autonomy_level(control, value, aliases)


def lane_action_registry(root: Path) -> dict[str, dict[str, Any]]:
    return wg_lane_action_registry(root)


def as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def format_lane_value(value: Any, mission_id: str) -> Any:
    if isinstance(value, str):
        return value.replace("{mission_id}", mission_id)
    if isinstance(value, list):
        return [format_lane_value(item, mission_id) for item in value]
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    return core_load_manifest(path)


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    return core_write_manifest(path, payload)


def unique(values: list[str]) -> list[str]:
    return core_unique(values)


def operation_type_tree(operation: dict[str, Any]) -> list[str]:
    return core_operation_type_tree(operation)


def validate_graph_operation_structure(operation: dict[str, Any], path: str = "graph_operation") -> list[str]:
    return core_validate_graph_operation_structure(operation, path)


def graph_operation_output_nodes(operation: dict[str, Any]) -> list[str]:
    return core_graph_operation_output_nodes(operation)


def graph_operation_input_nodes(operation: dict[str, Any]) -> list[str]:
    return core_graph_operation_input_nodes(operation)


def replace_template_values(value: Any, replacements: dict[str, str]) -> Any:
    return core_replace_template_values(value, replacements)


CONTRACT_PLACEHOLDER_RE = CORE_CONTRACT_PLACEHOLDER_RE


def contract_leaf_values(value: Any) -> list[Any]:
    return core_contract_leaf_values(value)


def contract_contains_placeholder(value: Any) -> bool:
    return core_contract_contains_placeholder(value)


def template_prefilled_role_verdict(verdict: dict[str, Any]) -> bool:
    return core_template_prefilled_role_verdict(verdict)


def scrub_template_role_verdicts(contract: dict[str, Any], *, template_mode: bool = False) -> bool:
    return core_scrub_template_role_verdicts(contract, template_mode=template_mode)


def contract_governance_conflict(contract: dict[str, Any]) -> bool:
    return core_contract_governance_conflict(contract)


def contract_hygiene_payload(contract: dict[str, Any]) -> dict[str, Any]:
    return core_contract_hygiene_payload(contract)


def contract_template_path(root: Path, template: str) -> Path:
    return core_contract_template_path(root, template, package_root=PACKAGE_ROOT)


def control_contract_document(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    return core_control_contract_document(path)


def set_path_value(document: dict[str, Any], target: str, value: Any, op: str) -> None:
    return core_set_path_value(document, target, value, op)


def upsert_by_id(items: list[dict[str, Any]], item: dict[str, Any]) -> str:
    return core_upsert_by_id(items, item)


def evidence_store_path(root: Path, mission_id: str, explicit: str | None = None) -> Path:
    return core_evidence_store_path(root, mission_id, explicit)


def load_evidence_store(path: Path, mission_id: str) -> dict[str, Any]:
    return core_load_evidence_store(path, mission_id)


def mission_slice_path(root: Path, mission_id: str) -> Path:
    return core_mission_slice_path(root, mission_id)


def load_mission_slice(root: Path, mission_id: str, entry: dict[str, Any] | None = None) -> tuple[Path, dict[str, Any]]:
    return core_load_mission_slice(root, mission_id, entry)


# Legacy stage-mode control plane derivation removed. Active missions now require an explicit
# Mission Slice; mission-status fields like current_stage are tracking
# data only and are no longer used to synthesize a control plane.


def active_mission_ids(status: dict[str, Any]) -> list[str]:
    return core_active_mission_ids(status)


def mission_entry_operation_completed(entry: dict[str, Any]) -> bool:
    return core_mission_entry_operation_completed(entry)


def open_mission_ids(status: dict[str, Any]) -> list[str]:
    return core_open_mission_ids(status)


def fail_payload(control: str, code: str, message: str) -> dict[str, Any]:
    return core_fail_payload(control, code, message)


def emit_payload(args: argparse.Namespace, payload: dict[str, Any]) -> int:
    return core_emit_payload(args, payload)


def finding(level: str, code: str, message: str, *, source: str = "", blocking: bool = False, **extra: Any) -> dict[str, Any]:
    return core_finding(level, code, message, source=source, blocking=blocking, **extra)


def status_from_findings(findings: list[dict[str, Any]]) -> str:
    return core_status_from_findings(findings)


def control_common_root(root: Path) -> Path:
    return core_control_common_root(root, common_root=COMMON_ROOT)


def explicit_runtime_config_path(runtime_root: Path) -> Path:
    return core_explicit_runtime_config_path(runtime_root)


def resolve_runtime_layout(root: Path | str, explicit_runtime: str | None = None) -> dict[str, Any]:
    return core_resolve_runtime_layout(root, explicit_runtime, common_root=COMMON_ROOT)


def control_runtime_root(layout: dict[str, Any]) -> Path:
    return core_control_runtime_root(layout)


def control_status_path(layout: dict[str, Any]) -> Path:
    return core_control_status_path(layout)


def control_graph_root(layout: dict[str, Any]) -> Path:
    return core_control_graph_root(layout)


def mission_summary(mission_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    return core_mission_summary(mission_id, entry)


def node_summary(path: Path, node: dict[str, Any]) -> dict[str, Any]:
    return core_node_summary(path, node)


def load_control_nodes(layout: dict[str, Any]) -> list[dict[str, Any]]:
    return core_load_control_nodes(layout)


def control_nodes_by_id(layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return core_control_nodes_by_id(layout)


def load_control_slice(layout: dict[str, Any], project_root: Path, mission_id: str, entry: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    return core_load_control_slice(layout, project_root, mission_id, entry)


def mission_slice_from_lane(mission_slice: dict[str, Any]) -> str:
    return core_mission_slice_from_lane(mission_slice)


def mission_slice_primary_nodes(mission_slice: dict[str, Any]) -> list[str]:
    return core_mission_slice_primary_nodes(mission_slice)


def mission_slice_lane_consistency_findings(
    nodes_by_id: dict[str, dict[str, Any]],
    mission_id: str,
    mission_slice: dict[str, Any],
    *,
    source: str,
    blocking: bool,
    path: str = "",
) -> list[dict[str, Any]]:
    return core_mission_slice_lane_consistency_findings(
        nodes_by_id,
        mission_id,
        mission_slice,
        source=source,
        blocking=blocking,
        path=path,
    )


def work_graph_nodes_by_id(root: Path) -> tuple[dict[str, dict[str, Any]], str | None]:
    nodes, _paths, findings = wg_load_nodes(wg_resolve_graph_root(root))
    if findings:
        return nodes, "; ".join(item.message for item in findings)
    return nodes, None


CHECKPOINT_ALIASES = {
    "acceptance_result": "acceptance-result",
    "tech_design": "tech-design",
    "execution_brief": "execution-brief",
    "verification_report": "verification-report",
    "delivery_package": "delivery-package",
    "code_review": "code-review",
    "mission_contract": "mission-contract",
    "dependency_impact": "dependency-impact",
}


def normalize_checkpoint(value: str) -> str:
    return core_normalize_checkpoint(value)


def checkpoint_names(value: Any) -> list[str]:
    return core_checkpoint_names(value)


def load_control_approval_records(layout: dict[str, Any]) -> list[dict[str, Any]]:
    return core_load_control_approval_records(layout)


def approved_checkpoints_for_mission(layout: dict[str, Any], mission_id: str) -> dict[str, str]:
    return core_approved_checkpoints_for_mission(layout, mission_id)


def gate_report_paths(layout: dict[str, Any]) -> list[Path]:
    return core_gate_report_paths(layout)


def load_control_gate_reports(layout: dict[str, Any], mission_ids: set[str]) -> list[dict[str, Any]]:
    return core_load_control_gate_reports(layout, mission_ids)


def collect_required_approvals(root: Path, layout: dict[str, Any], status_doc: dict[str, Any], active_ids: list[str], active_slices: list[dict[str, Any]], pending_gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return core_collect_required_approvals(root, layout, status_doc, active_ids, active_slices, pending_gates)


def control_active_slice_ids(status_doc: dict[str, Any], root: Path, layout: dict[str, Any]) -> list[str]:
    return core_control_active_slice_ids(status_doc, root, layout)


def collect_control_status(root: Path, layout: dict[str, Any], *, mission: str | None = None) -> dict[str, Any]:
    return core_collect_control_status(root, layout, mission=mission)


def node_status_by_id(status_payload: dict[str, Any]) -> dict[str, str]:
    return core_node_status_by_id(status_payload)


def build_continue_candidates(root: Path, layout: dict[str, Any], *, mission: str | None = None) -> dict[str, Any]:
    return core_build_continue_candidates(root, layout, mission=mission)


GUIDANCE_CATEGORIES = CORE_GUIDANCE_CATEGORIES


def control_relpath(root: Path, path: Path) -> str:
    return core_control_relpath(root, path)


def path_item(root: Path, kind: str, path_value: str, *, required: bool, source: str) -> dict[str, Any]:
    return core_path_item(root, kind, path_value, required=required, source=source)


def selected_mission_slice(root: Path, layout: dict[str, Any], mission_id: str) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, Any]]:
    return core_selected_mission_slice(root, layout, mission_id)


def latest_gate_report_for_mission(layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    return core_latest_gate_report_for_mission(layout, mission_id)


def load_advance_after_gate_module() -> Any | None:
    return core_load_advance_after_gate_module()


def next_graph_operation_for_frame(root: Path, mission_id: str, mission_slice: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return core_next_graph_operation_for_frame(root, mission_id, mission_slice)


def build_control_frame(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    return core_build_control_frame(root, layout, mission_id)


def build_context_index(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    return core_build_context_index(root, layout, mission_id)


def guidance_required_controls(
    *,
    missing_context: list[dict[str, Any]],
    missing_artifacts: list[dict[str, Any]],
    required_approvals: list[dict[str, Any]],
    missing_evidence: list[dict[str, Any]],
    pending_gates: list[dict[str, Any]],
) -> list[str]:
    return core_guidance_required_controls(
        missing_context=missing_context,
        missing_artifacts=missing_artifacts,
        required_approvals=required_approvals,
        missing_evidence=missing_evidence,
        pending_gates=pending_gates,
    )


def stage_participation_policy_payload(frame: dict[str, Any]) -> dict[str, Any]:
    return core_stage_participation_policy_payload(frame)


def entered_stage_obligations_payload(frame: dict[str, Any], required_controls: list[str]) -> dict[str, Any]:
    return core_entered_stage_obligations_payload(frame, required_controls)


def missing_review_evidence(root: Path, layout: dict[str, Any], mission_id: str, required_review_roles: list[str]) -> list[dict[str, Any]]:
    return core_missing_review_evidence(root, layout, mission_id, required_review_roles)


def blocked_guidance_payload(root: Path, layout: dict[str, Any], mission_id: str, frame: dict[str, Any]) -> dict[str, Any]:
    return core_blocked_guidance_payload(root, layout, mission_id, frame)


def build_control_guidance(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    return core_build_control_guidance(root, layout, mission_id)


def build_lane_action_payload(action_name: str, action: dict[str, Any], mission_id: str) -> dict[str, Any]:
    return core_build_lane_action_payload(action_name, action, mission_id)


def resolve_lane_stage(root: Path, action_name: str) -> tuple[str, str, dict[str, Any] | None]:
    config = load_runtime_config(root)
    actions = lane_action_registry(root)
    if action_name in actions:
        action = actions[action_name]
        return action_name, str(action.get("stage") or ""), action
    lane = wg_lane_of_stage(config, action_name)
    if lane:
        resolved_lane, stage, action = wg_lane_stage_for_node(config, {"id": "<mission-slice>", "lane": lane, "stage": action_name})
        return resolved_lane, stage, action
    return "", "", None


def write_mission_status_for_slice(root: Path, mission_id: str, slice_payload: dict[str, Any], slice_path: Path) -> dict[str, Any]:
    from harness_cli_core.domain.mission import write_mission_status_for_slice as core_write_mission_status_for_slice

    return core_write_mission_status_for_slice(root, mission_id, slice_payload, slice_path, today_value=today())


def remove_node_references(node: dict[str, Any], removed: set[str]) -> None:
    from harness_cli_core.domain.mission import remove_node_references as core_remove_node_references

    core_remove_node_references(node, removed)


def reset_mission_stage(
    root: Path,
    mission_id: str,
    stage: str,
    primary_nodes: list[str],
    related_nodes: list[str],
    output_node_policy: str,
    preserve_stage_history: bool,
    preserve_checkpoints: bool,
    reason: str,
) -> dict[str, Any]:
    from harness_cli_core.domain.mission import reset_mission_stage as core_reset_mission_stage

    def load_graph() -> tuple[Path, dict[str, dict[str, Any]], dict[str, Path], str | None]:
        graph_root = wg_resolve_graph_root(root)
        nodes, paths, findings = wg_load_nodes(graph_root)
        if findings:
            return graph_root, nodes, paths, "; ".join(item.message for item in findings)
        return graph_root, nodes, paths, None

    def run_graph_check() -> tuple[int, str]:
        graph_check = run_python_capture(script("work-graph", "scripts", "check_graph_consistency.py"), ["--root", str(root), "--json"])
        return graph_check.returncode, graph_check.stdout

    return core_reset_mission_stage(
        root,
        mission_id,
        stage,
        primary_nodes,
        related_nodes,
        output_node_policy,
        preserve_stage_history,
        preserve_checkpoints,
        reason,
        resolve_lane_stage=lambda stage_name: resolve_lane_stage(root, stage_name),
        load_graph=load_graph,
        write_views=wg_write_views,
        run_graph_check=run_graph_check,
        now_value=now_iso(),
        today_value=today(),
    )


def cmd_mission_reset_stage(args: argparse.Namespace) -> int:
    return core_mission_handlers.cmd_mission_reset_stage(args)


def cmd_mission_create_slice(args: argparse.Namespace) -> int:
    return core_mission_handlers.cmd_mission_create_slice(args)


def cmd_mission_status(args: argparse.Namespace) -> int:
    return core_mission_handlers.cmd_mission_status(args)


def cmd_mission_stage_start(args: argparse.Namespace) -> int:
    return core_mission_handlers.cmd_mission_stage_start(args)


def cmd_mission_stage_complete(args: argparse.Namespace) -> int:
    return core_mission_handlers.cmd_mission_stage_complete(args)


def cmd_mission_init(args: argparse.Namespace) -> int:
    return core_mission_handlers.cmd_mission_init(args)


def project_context_path(root: Path) -> Path:
    return core_project_context_path(root)


def project_context_template_path(root: Path) -> Path:
    return core_project_context_template_path(root)


def project_knowledge_root(root: Path) -> Path:
    return core_project_knowledge_root(root)


def project_knowledge_template_root() -> Path:
    return core_project_knowledge_template_root()


def behavior_specs_root(root: Path) -> Path:
    return core_behavior_specs_root(root)


def behavior_specs_template_root() -> Path:
    return core_behavior_specs_template_root()


def _knowledge_index_rows(root: Path) -> list[dict[str, str]]:
    return core_knowledge_index_rows(root)


def _render_knowledge_index(root: Path) -> str:
    return core_render_knowledge_index(root)


def _knowledge_promotion_candidates(root: Path, mission: str) -> list[dict[str, str]]:
    return core_knowledge_promotion_candidates(root, mission)


def cmd_mission_close(args: argparse.Namespace) -> int:
    return core_mission_handlers.cmd_mission_close(args)


def approvals_path(root: Path) -> Path:
    return core_approvals_path(root)


def load_approvals(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return core_load_approvals(root)


def write_approvals(root: Path, document: dict[str, Any], records: list[dict[str, Any]]) -> Path:
    return core_write_approvals(root, document, records)


def next_approval_id(records: list[dict[str, Any]]) -> str:
    return core_next_approval_id(records)


def checkpoint_name(args: argparse.Namespace) -> str:
    return core_checkpoint_name(args)


def sync_checkpoint_passed(root: Path, mission_id: str, checkpoint: str) -> dict[str, Any] | None:
    return core_sync_checkpoint_passed(root, mission_id, checkpoint)


def stage_completion_config(root: Path) -> dict[str, Any]:
    return core_stage_completion_config(root)


def approval_stage_completion_status(root: Path, mission_id: str, record: dict[str, Any], mission_status: dict[str, Any] | None) -> dict[str, Any]:
    return core_approval_stage_completion_status(root, mission_id, record, mission_status)


def mission_stage_completion_status(root: Path, stage: str, mission_status: dict[str, Any] | None) -> dict[str, Any]:
    return core_mission_stage_completion_status(root, stage, mission_status)


def approval_matches(record: dict[str, Any], *, mission: str | None = None, approval_type: str | None = None, stage: str | None = None, status: str | None = None) -> bool:
    return core_approval_matches(record, mission=mission, approval_type=approval_type, stage=stage, status=status)


def detect_model_adapter(requested: str, adapters: dict[str, Any]) -> tuple[str, str]:
    return core_detect_model_adapter(requested, adapters)


def model_policy_defaults(model_routing: dict[str, Any], adapter_config: dict[str, Any], kind: str) -> dict[str, Any]:
    return core_model_policy_defaults(model_routing, adapter_config, kind)


def resolve_role_model_policy(
    role: str,
    kind: str,
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return core_resolve_role_model_policy(role, kind, adapter_config, model_defaults)


def add_role_model_policy(
    policies: dict[str, dict[str, Any]],
    role: str,
    kind: str,
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> None:
    return core_add_role_model_policy(policies, role, kind, adapter_config, model_defaults)


def professional_role_model_policies(
    professional_roles: dict[str, Any],
    work_graph: dict[str, Any],
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return core_professional_role_model_policies(professional_roles, work_graph, adapter_config, model_defaults)


def cmd_contract_check(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_check(args)


def cmd_contract_init(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_init(args)


def cmd_contract_fill(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_fill(args)


def cmd_contract_patch(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_patch(args)


def cmd_contract_add_verdict(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_add_verdict(args)


def cmd_contract_add_execution_result(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_add_execution_result(args)


# breakdown-improvement-plan M1.4: execution-brief → execute permission
# overlay translator. M5 will deliver the full translator behind the
# `harness execute apply-overlay --mission <id>` CLI; M1.4 lays down the
# function signature + interface contract referenced by the
# permission-overlay-translation protocol so downstream stages can bind to a
# stable API. The skeleton implementation walks each task's
# authorized_paths / prohibited_paths / stop_if and returns a settings
# overlay dict ready for merge into .claude/settings.json. Complex glob
# patterns (containing `**` or `!` negation) fall back to `ask` and the
# fallback is reported via the returned `fallback_log` field; trace-log
# integration is deferred to M5.
def translate_execution_brief_to_overlay(
    execution_brief_contract: dict,
    *,
    task_id: str | None = None,
) -> dict:
    return core_translate_execution_brief_to_overlay(execution_brief_contract, task_id=task_id)


# --- execute-improvement-plan M2.1 / M5 anchor: apply-overlay, stop-event ---
# CROSS-STAGE-OVERLAY-PROTOCOL anchor commands. `apply-overlay` reads the
# breakdown-side execution-brief.contract.yaml, calls
# translate_execution_brief_to_overlay, and writes the effective overlay to
# `harness-runtime/harness/stages/<mission>/runtime/effective-overlay.json`
# so the stop_if hooks (check_stop_*.py) can consume per-task authorized /
# prohibited / stop_if state at PreToolUse time.

def cmd_execute_apply_overlay(args: argparse.Namespace) -> int:
    return core_execute_handlers.cmd_execute_apply_overlay(args)


def cmd_execute_revoke_overlay(args: argparse.Namespace) -> int:
    return core_execute_handlers.cmd_execute_revoke_overlay(args)


def cmd_execute_stop_event_record(args: argparse.Namespace) -> int:
    return core_execute_handlers.cmd_execute_stop_event_record(args)


from harness_cli_core.app.commands.agent_handlers import (  # noqa: E402
    AGENT_DISPATCH_EXIT_OK as _AGENT_DISPATCH_EXIT_OK,
    AGENT_DISPATCH_EXIT_ARG_INVALID as _AGENT_DISPATCH_EXIT_ARG_INVALID,
    AGENT_DISPATCH_EXIT_WORKSPACE_LOCK as _AGENT_DISPATCH_EXIT_WORKSPACE_LOCK,
    AGENT_DISPATCH_EXIT_ADAPTER_UNAVAILABLE as _AGENT_DISPATCH_EXIT_ADAPTER_UNAVAILABLE,
)
from harness_cli_core.domain.runs import (  # noqa: E402
    append_control_event as _append_control_event,
    new_run_id as _agent_dispatch_run_id,
)


def cmd_agent_dispatch(args: argparse.Namespace) -> int:
    return core_cmd_agent_dispatch(args)


def cmd_run_cancel(args: argparse.Namespace) -> int:
    return core_cmd_run_cancel(args)


def cmd_run_retry(args: argparse.Namespace) -> int:
    return core_cmd_run_retry(args)


def cmd_mission_artifacts_append(args: argparse.Namespace) -> int:
    return core_cmd_mission_artifacts_append(args)


def cmd_acceptance_record(args: argparse.Namespace) -> int:
    return core_cmd_acceptance_record(args)


def cmd_execute_check_ready(args: argparse.Namespace) -> int:
    return core_execute_handlers.cmd_execute_check_ready(args)


def cmd_execute_gate_run(args: argparse.Namespace) -> int:
    return core_execute_handlers.cmd_execute_gate_run(args)


# --- code-review-improvement-plan M2.1: `harness review ...` ----------------


def cmd_review_check_ready(args: argparse.Namespace) -> int:
    return core_cmd_review_check_ready(args)


def cmd_review_select_reviewers(args: argparse.Namespace) -> int:
    return core_cmd_review_select_reviewers(args)


def cmd_review_snapshot_diff(args: argparse.Namespace) -> int:
    return core_cmd_review_snapshot_diff(args)


def cmd_review_toolchain_status(args: argparse.Namespace) -> int:
    return core_cmd_review_toolchain_status(args)


def cmd_review_e2e_status(args: argparse.Namespace) -> int:
    return core_cmd_review_e2e_status(args)


def cmd_contract_add_round(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_add_round(args)


def cmd_contract_check_finding_ownership(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_check_finding_ownership(args)


def cmd_contract_detect_conflicts(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_detect_conflicts(args)


def cmd_trace_round_enter(args: argparse.Namespace) -> int:
    return core_trace_handlers.cmd_trace_round_enter(args)


def cmd_trace_round_exit(args: argparse.Namespace) -> int:
    return core_trace_handlers.cmd_trace_round_exit(args)


# --- end code-review-improvement-plan M2.1 ----------------------------------


# --- breakdown-improvement-plan M2.1: real-new CLI commands -----------------
# Five commands carry the breakdown stage's typed lifecycle into harness-cli:
# - `execution-brief gate run` merges Step 7 quality_check + Step 8 artifact_gate
# - `execution-brief self-check` is the lighter Step 7 rapid lint
# - `writing-plans run --mode internal-carrier` is the typed entry into the
#    writing-plans carrier; only callable from the breakdown stage
# - `spec diff list` enumerates delta specs and their coverage state
# - `execution-brief check-coverage --spec-mode strict` is the global
#    coverage gate when spec.enabled=true
#
# These commands keep their semantics typed and JSON-only so the
# harness-cli skill can consume them without parsing free text. Heavy
# downstream semantics (e.g. full Atomic Task Queue 12-field lint,
# parallel write_scope conflict detection) are wired into M4.2 lints; M2.1
# commands stop at the structural / completeness layer that the workflow
# needs at runtime.


def cmd_execution_brief_self_check(args: argparse.Namespace) -> int:
    return core_execution_brief_handlers.cmd_execution_brief_self_check(args)


def cmd_execution_brief_gate_run(args: argparse.Namespace) -> int:
    return core_execution_brief_handlers.cmd_execution_brief_gate_run(args)


def cmd_writing_plans_run(args: argparse.Namespace) -> int:
    return core_writing_plans_handlers.cmd_writing_plans_run(args)


def cmd_spec_diff_list(args: argparse.Namespace) -> int:
    return core_cmd_spec_diff_list(args)


def cmd_execution_brief_check_coverage(args: argparse.Namespace) -> int:
    return core_execution_brief_handlers.cmd_execution_brief_check_coverage(args)


# --- M2.1 chunk A: intake-workflow CLI commands ----------------------------
# These commands enable the Option B 6-phase intake workflow rewrite. Each
# returns typed `{status, control, ...}` JSON via emit_payload so callers can
# consume them through the harness-cli skill without parsing free text.

import re as _re

_MISSION_ID_SLUG_RE = _re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def cmd_mission_new_id(args: argparse.Namespace) -> int:
    return core_mission_handlers.cmd_mission_new_id(args)


def cmd_trace_log_init(args: argparse.Namespace) -> int:
    return core_trace_handlers.cmd_trace_log_init(args)


def cmd_trace_step_enter(args: argparse.Namespace) -> int:
    return core_trace_handlers.cmd_trace_step_enter(args)


def cmd_trace_step_exit(args: argparse.Namespace) -> int:
    return core_trace_handlers.cmd_trace_step_exit(args)


def cmd_todo_report(args: argparse.Namespace) -> int:
    return core_todo_handlers.cmd_todo_report(args)


def cmd_todo_sync(args: argparse.Namespace) -> int:
    return core_todo_handlers.cmd_todo_sync(args)


def cmd_contract_summary(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_summary(args)


def cmd_contract_check_recheck_pending(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_check_recheck_pending(args)


def cmd_evidence_graph_check(args: argparse.Namespace) -> int:
    return core_cmd_evidence_graph_check(args)


def cmd_evidence_graph_build(args: argparse.Namespace) -> int:
    return core_cmd_evidence_graph_build(args)


def cmd_evidence_add(args: argparse.Namespace) -> int:
    return core_cmd_evidence_add(args)


def cmd_evidence_link(args: argparse.Namespace) -> int:
    return core_cmd_evidence_link(args)


def cmd_evidence_command_collect(args: argparse.Namespace) -> int:
    return core_cmd_evidence_command_collect(args)


def cmd_evidence_visual_manifest(args: argparse.Namespace) -> int:
    return core_cmd_evidence_visual_manifest(args)


def cmd_gate_advance(args: argparse.Namespace) -> int:
    return core_cmd_gate_advance(args)


def cmd_gate_run(args: argparse.Namespace) -> int:
    return core_cmd_gate_run(args)


def cmd_gate_transition(args: argparse.Namespace) -> int:
    return core_cmd_gate_transition(args)


def cmd_gate_report_render(args: argparse.Namespace) -> int:
    return core_cmd_gate_report_render(args)


def cmd_gate_control_reports(args: argparse.Namespace) -> int:
    return core_cmd_gate_control_reports(args)


# ----------------------------------------------------------------------------
# PRD anti-pattern + domain-model + agent-cap-eval handlers live in
# harness_cli_core.app.commands.prd_handlers; thin delegators below.


def cmd_prd_anti_pattern_scan(args: argparse.Namespace) -> int:
    return core_cmd_prd_anti_pattern_scan(args)


def cmd_prd_domain_model_lint(args: argparse.Namespace) -> int:
    return core_cmd_prd_domain_model_lint(args)


def cmd_spec_delta_lint(args: argparse.Namespace) -> int:
    return core_cmd_spec_delta_lint(args)


def cmd_spec_scan_from_prd(args: argparse.Namespace) -> int:
    return core_cmd_spec_scan_from_prd(args)


def cmd_prd_agent_cap_eval(args: argparse.Namespace) -> int:
    return core_cmd_prd_agent_cap_eval(args)

# ----------------------------------------------------------------------------
# Discovery + solution stage commands — thin delegators to
# harness_cli_core.app.commands.discovery_handlers / solution_handlers.


def cmd_graphify_status(args: argparse.Namespace) -> int:
    return core_cmd_graphify_status(args)


def cmd_discovery_skip(args: argparse.Namespace) -> int:
    return core_cmd_discovery_skip(args)


def cmd_discovery_check_dependency_trigger(args: argparse.Namespace) -> int:
    return core_cmd_discovery_check_dependency_trigger(args)


def cmd_discovery_agent_eng_eval(args: argparse.Namespace) -> int:
    return core_cmd_discovery_agent_eng_eval(args)


def cmd_solution_decision_scan(args: argparse.Namespace) -> int:
    return core_cmd_solution_decision_scan(args)


def cmd_solution_lane_action_validate(args: argparse.Namespace) -> int:
    return core_cmd_solution_lane_action_validate(args)


def cmd_spec_scan_capabilities(args: argparse.Namespace) -> int:
    return core_cmd_spec_scan_capabilities(args)


def cmd_spec_scan(args: argparse.Namespace) -> int:
    return core_cmd_spec_scan(args)


# --- interaction / prototype-as-frontend / alignment / tech-design lane CLIs
# (delegated to harness_cli_core.app.commands.*_handlers)


def cmd_interaction_check_ui_trigger(args: argparse.Namespace) -> int:
    return core_cmd_interaction_check_ui_trigger(args)


def cmd_interaction_spec_check(args: argparse.Namespace) -> int:
    return core_cmd_interaction_spec_check(args)


def cmd_interaction_ux_quality_check(args: argparse.Namespace) -> int:
    return core_cmd_interaction_ux_quality_check(args)


def cmd_interaction_feedback_sync_check(args: argparse.Namespace) -> int:
    return core_cmd_interaction_feedback_sync_check(args)


def cmd_interaction_visual_coverage_check(args: argparse.Namespace) -> int:
    return core_cmd_interaction_visual_coverage_check(args)


def cmd_interaction_trace_coverage_check(args: argparse.Namespace) -> int:
    return core_cmd_interaction_trace_coverage_check(args)


def cmd_interaction_prototype_check(args: argparse.Namespace) -> int:
    return core_cmd_interaction_prototype_check(args)


def cmd_interaction_project(args: argparse.Namespace) -> int:
    return core_cmd_interaction_project(args)


def cmd_interaction_resolve_feedback(args: argparse.Namespace) -> int:
    return core_cmd_interaction_resolve_feedback(args)


def cmd_interaction_locator_check(args: argparse.Namespace) -> int:
    return core_cmd_interaction_locator_check(args)


def cmd_alignment_check(args: argparse.Namespace) -> int:
    return core_cmd_alignment_check(args)


def cmd_interaction_gate_run(args: argparse.Namespace) -> int:
    return core_cmd_interaction_gate_run(args)


def cmd_prototype_as_frontend_changeset_check(args: argparse.Namespace) -> int:
    return core_cmd_prototype_as_frontend_changeset_check(args)


def cmd_prototype_as_frontend_path_check(args: argparse.Namespace) -> int:
    return core_cmd_prototype_as_frontend_path_check(args)


def cmd_prototype_as_frontend_drift_check(args: argparse.Namespace) -> int:
    return core_cmd_prototype_as_frontend_drift_check(args)


def cmd_prototype_as_frontend_gate_run(args: argparse.Namespace) -> int:
    return core_cmd_prototype_as_frontend_gate_run(args)


def cmd_tech_design_check_dep_impact_trigger(args: argparse.Namespace) -> int:
    return core_cmd_tech_design_check_dep_impact_trigger(args)


def cmd_tech_design_check_capability_trigger(args: argparse.Namespace) -> int:
    return core_cmd_tech_design_check_capability_trigger(args)



def cmd_discovery_summary(args: argparse.Namespace) -> int:
    return core_cmd_discovery_summary(args)


# ---------------------------------------------------------------------------
# verify-improvement-plan M2.1: verify command domain
# ---------------------------------------------------------------------------

def cmd_verify_compute_scope(args: argparse.Namespace) -> int:
    return core_cmd_verify_compute_scope(args)


def cmd_verify_run_tests(args: argparse.Namespace) -> int:
    return core_cmd_verify_run_tests(args)


def cmd_verify_e2e_status(args: argparse.Namespace) -> int:
    return core_cmd_verify_e2e_status(args)


def cmd_verify_dispatch_worker(args: argparse.Namespace) -> int:
    return core_cmd_verify_dispatch_worker(args)


def cmd_verify_dispatch_reviewer(args: argparse.Namespace) -> int:
    return core_cmd_verify_dispatch_reviewer(args)


def cmd_verify_detect_contradictions(args: argparse.Namespace) -> int:
    return core_cmd_verify_detect_contradictions(args)


def cmd_verify_compute_conclusion(args: argparse.Namespace) -> int:
    return core_cmd_verify_compute_conclusion(args)


def cmd_verify_agent_eval_status(args: argparse.Namespace) -> int:
    return core_cmd_verify_agent_eval_status(args)


def cmd_verify_failure_path(args: argparse.Namespace) -> int:
    return core_cmd_verify_failure_path(args)


def cmd_verify_true_e2e_check(args: argparse.Namespace) -> int:
    return core_cmd_verify_true_e2e_check(args)


def cmd_verify_prototype_alignment_check(args: argparse.Namespace) -> int:
    return core_cmd_verify_prototype_alignment_check(args)


def cmd_verify_gate_run(args: argparse.Namespace) -> int:
    return core_cmd_verify_gate_run(args)


def cmd_contract_check_acceptance_trace(args: argparse.Namespace) -> int:
    return core_contract_handlers.cmd_contract_check_acceptance_trace(args)



# ----------------------------------------------------------------------------
# Retrospective stage commands (retrospective-improvement-plan M2.1)
# ----------------------------------------------------------------------------


def cmd_mission_artifacts(args: argparse.Namespace) -> int:
    return core_cmd_mission_artifacts(args)


def cmd_mission_retrospective_data(args: argparse.Namespace) -> int:
    return core_cmd_mission_retrospective_data(args)


def cmd_project_context_add_lesson(args: argparse.Namespace) -> int:
    return core_cmd_project_context_add_lesson(args)


def cmd_project_context_drift_scan(args: argparse.Namespace) -> int:
    return core_cmd_project_context_drift_scan(args)


def cmd_project_context_lint(args: argparse.Namespace) -> int:
    return core_cmd_project_context_lint(args)


def cmd_retrospective_harness_gap_init(args: argparse.Namespace) -> int:
    return core_cmd_retrospective_harness_gap_init(args)


def cmd_retrospective_harness_gap_emit(args: argparse.Namespace) -> int:
    return core_cmd_retrospective_harness_gap_emit(args)


def cmd_harness_gap_pattern_scan(args: argparse.Namespace) -> int:
    return core_cmd_harness_gap_pattern_scan(args)


def cmd_agent_eval_drift(args: argparse.Namespace) -> int:
    return core_cmd_agent_eval_drift(args)



# ----------------------------------------------------------------------------
# finishing-branch stage commands (finishing-branch-improvement-plan M2.1)
# ----------------------------------------------------------------------------


def cmd_finishing_branch_status(args: argparse.Namespace) -> int:
    return core_cmd_finishing_branch_status(args)


def cmd_finishing_branch_detect_test_cmd(args: argparse.Namespace) -> int:
    return core_cmd_finishing_branch_detect_test_cmd(args)


def cmd_finishing_branch_run_tests(args: argparse.Namespace) -> int:
    return core_cmd_finishing_branch_run_tests(args)


def cmd_finishing_branch_readiness(args: argparse.Namespace) -> int:
    return core_cmd_finishing_branch_readiness(args)


def cmd_finishing_branch_options(args: argparse.Namespace) -> int:
    return core_cmd_finishing_branch_options(args)


def cmd_finishing_branch_pr_body(args: argparse.Namespace) -> int:
    return core_cmd_finishing_branch_pr_body(args)


def cmd_finishing_branch_execute(args: argparse.Namespace) -> int:
    return core_cmd_finishing_branch_execute(args)


def cmd_finishing_branch_cleanup(args: argparse.Namespace) -> int:
    return core_cmd_finishing_branch_cleanup(args)


def cmd_delivery_summarize(args: argparse.Namespace) -> int:
    return core_cmd_delivery_summarize(args)


def cmd_delivery_compute_follow_ups(args: argparse.Namespace) -> int:
    return core_cmd_delivery_compute_follow_ups(args)


def cmd_delivery_check_followups(args: argparse.Namespace) -> int:
    return core_cmd_delivery_check_followups(args)


def cmd_delivery_compute_conclusion(args: argparse.Namespace) -> int:
    return core_cmd_delivery_compute_conclusion(args)


def cmd_delivery_handoff(args: argparse.Namespace) -> int:
    return core_cmd_delivery_handoff(args)


def cmd_delivery_agent_capability_status(args: argparse.Namespace) -> int:
    return core_cmd_delivery_agent_capability_status(args)


def add_leaf(subparsers: argparse._SubParsersAction, name: str, handler: Callable[[argparse.Namespace], int], **kwargs: object) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, **kwargs)
    parser.set_defaults(handler=handler)
    add_common(parser)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("--root", dest="global_root", default=".", help="target project root")
    sub = parser.add_subparsers(dest="command", required=True)

    register_frame_commands(
        sub,
        add_leaf,
        FrameCommandHandlers(current=cmd_frame_current, explain=cmd_frame_explain),
    )

    register_config_commands(
        sub,
        add_leaf,
        ConfigCommandHandlers(snapshot=cmd_config_snapshot, diff=cmd_config_diff, migrate=cmd_config_migrate),
    )

    register_control_commands(
        sub,
        add_leaf,
        ControlCommandHandlers(
            status=cmd_control_status,
            candidates=cmd_control_candidates,
            frame=cmd_control_frame,
            guidance=cmd_control_guidance,
            context_index=cmd_control_context_index,
        ),
    )

    register_context_commands(
        sub,
        add_leaf,
        ContextCommandHandlers(check=cmd_context_check, init=cmd_context_init),
    )

    register_knowledge_commands(
        sub,
        add_leaf,
        KnowledgeCommandHandlers(
            init=cmd_knowledge_init,
            check=cmd_knowledge_check,
            index=cmd_knowledge_index,
            resolve=cmd_knowledge_resolve,
            promote=cmd_knowledge_promote,
        ),
    )

    register_spec_commands(
        sub,
        add_leaf,
        SpecCommandHandlers(
            check=cmd_spec_check,
            init=cmd_spec_init,
            delta_lint=cmd_spec_delta_lint,
            scan=cmd_spec_scan,
            diff_list=cmd_spec_diff_list,
        ),
    )

    register_execution_brief_commands(
        sub,
        add_leaf,
        ExecutionBriefCommandHandlers(
            self_check=core_execution_brief_handlers.cmd_execution_brief_self_check,
            check_coverage=core_execution_brief_handlers.cmd_execution_brief_check_coverage,
            gate_run=core_execution_brief_handlers.cmd_execution_brief_gate_run,
        ),
    )

    # execute-improvement-plan M5 anchor: apply-overlay / revoke-overlay /
    # stop-event.record. These commands consume the breakdown-side
    # execution-brief.contract.yaml and write the effective overlay state +
    # stop event records the runtime hooks read.
    # PT-CLI-EXTEND-01: harness agent dispatch — typed action shim invoked by
    # TheForce server CLI Bridge. Records dispatch_agent_run intent in the
    # workspace runtime ledger and emits {run_id, status}; Adapter execution
    # itself happens server-side.
    register_agent_commands(
        sub,
        add_leaf,
        AgentCommandHandlers(dispatch=cmd_agent_dispatch),
    )

    # PT-CLI-EXTEND-02: harness run cancel / retry — CLI Bridge shims for
    # AgentRun lifecycle typed actions (INV-09 retry never overwrites old Run;
    # SOL-RISK-002 cancel degrades honestly when backend cannot cancel).
    register_run_commands(
        sub,
        add_leaf,
        RunCommandHandlers(cancel=cmd_run_cancel, retry=cmd_run_retry),
    )

    register_execute_commands(
        sub,
        add_leaf,
        ExecuteCommandHandlers(
            apply_overlay=core_execute_handlers.cmd_execute_apply_overlay,
            revoke_overlay=core_execute_handlers.cmd_execute_revoke_overlay,
            check_ready=core_execute_handlers.cmd_execute_check_ready,
            gate_run=core_execute_handlers.cmd_execute_gate_run,
            stop_event_record=core_execute_handlers.cmd_execute_stop_event_record,
        ),
    )

    # code-review-improvement-plan M2.1: review readiness gate.
    register_review_commands(
        sub,
        add_leaf,
        ReviewCommandHandlers(
            check_ready=cmd_review_check_ready,
            select_reviewers=cmd_review_select_reviewers,
            snapshot_diff=cmd_review_snapshot_diff,
            toolchain_status=cmd_review_toolchain_status,
            e2e_status=cmd_review_e2e_status,
        ),
    )

    register_writing_plans_commands(
        sub,
        add_leaf,
        WritingPlansCommandHandlers(run=core_writing_plans_handlers.cmd_writing_plans_run),
    )

    register_mission_commands(
        sub,
        add_leaf,
        MissionCommandHandlers(
            init=core_mission_handlers.cmd_mission_init,
            create_slice=core_mission_handlers.cmd_mission_create_slice,
            status=core_mission_handlers.cmd_mission_status,
            reset_stage=core_mission_handlers.cmd_mission_reset_stage,
            stage_start=core_mission_handlers.cmd_mission_stage_start,
            stage_complete=core_mission_handlers.cmd_mission_stage_complete,
            close=core_mission_handlers.cmd_mission_close,
            new_id=core_mission_handlers.cmd_mission_new_id,
            artifacts=cmd_mission_artifacts,
            document=core_mission_handlers.cmd_mission_document,
            retrospective_data=cmd_mission_retrospective_data,
            artifacts_append=cmd_mission_artifacts_append,
        ),
    )

    register_trace_commands(
        sub,
        add_leaf,
        TraceCommandHandlers(
            log_init=core_trace_handlers.cmd_trace_log_init,
            report=core_trace_handlers.cmd_trace_report,
            step_enter=core_trace_handlers.cmd_trace_step_enter,
            step_exit=core_trace_handlers.cmd_trace_step_exit,
            round_enter=core_trace_handlers.cmd_trace_round_enter,
            round_exit=core_trace_handlers.cmd_trace_round_exit,
        ),
    )

    register_todo_commands(
        sub,
        add_leaf,
        TodoCommandHandlers(
            report=core_todo_handlers.cmd_todo_report,
            sync=core_todo_handlers.cmd_todo_sync,
        ),
    )

    register_approval_commands(
        sub,
        add_leaf,
        ApprovalCommandHandlers(
            append=cmd_approval_append,
            latest=cmd_approval_latest,
            require=cmd_approval_require,
        ),
    )

    register_clarification_commands(
        sub,
        add_leaf,
        ClarificationCommandHandlers(
            record=cmd_clarification_record,
            list=cmd_clarification_list,
        ),
    )

    register_graph_commands(
        sub,
        add_leaf,
        GraphCommandHandlers(
            apply=cmd_graph_apply,
            plan=cmd_graph_plan,
            rebuild=cmd_graph_rebuild,
            check=cmd_graph_check,
            node_show=cmd_graph_node_show,
            node_create=cmd_graph_node_create,
        ),
    )

    register_board_commands(sub, add_leaf, BoardCommandHandlers(select=cmd_board_select))

    register_contract_commands(
        sub,
        add_leaf,
        ContractCommandHandlers(
            init=core_contract_handlers.cmd_contract_init,
            fill=core_contract_handlers.cmd_contract_fill,
            patch=core_contract_handlers.cmd_contract_patch,
            add_verdict=core_contract_handlers.cmd_contract_add_verdict,
            record_review=core_contract_handlers.cmd_contract_record_review,
            add_execution_result=core_contract_handlers.cmd_contract_add_execution_result,
            check=core_contract_handlers.cmd_contract_check,
            summary=core_contract_handlers.cmd_contract_summary,
            check_recheck_pending=core_contract_handlers.cmd_contract_check_recheck_pending,
            add_round=core_contract_handlers.cmd_contract_add_round,
            check_finding_ownership=core_contract_handlers.cmd_contract_check_finding_ownership,
            detect_conflicts=core_contract_handlers.cmd_contract_detect_conflicts,
            check_acceptance_trace=core_contract_handlers.cmd_contract_check_acceptance_trace,
            check_disputes=core_contract_handlers.cmd_contract_check_disputes,
        ),
    )

    # verify-improvement-plan M2.1: verify command domain
    register_verify_commands(
        sub,
        add_leaf,
        VerifyCommandHandlers(
            compute_scope=cmd_verify_compute_scope,
            run_tests=cmd_verify_run_tests,
            e2e_status=cmd_verify_e2e_status,
            true_e2e_check=cmd_verify_true_e2e_check,
            dispatch_worker=cmd_verify_dispatch_worker,
            dispatch_reviewer=cmd_verify_dispatch_reviewer,
            detect_contradictions=cmd_verify_detect_contradictions,
            compute_conclusion=cmd_verify_compute_conclusion,
            agent_eval_status=cmd_verify_agent_eval_status,
            failure_path=cmd_verify_failure_path,
            prototype_alignment_check=cmd_verify_prototype_alignment_check,
            gate_run=cmd_verify_gate_run,
        ),
    )

    register_evidence_commands(
        sub,
        add_leaf,
        EvidenceCommandHandlers(
            graph_build=cmd_evidence_graph_build,
            graph_check=cmd_evidence_graph_check,
            add=cmd_evidence_add,
            link=cmd_evidence_link,
            command_collect=cmd_evidence_command_collect,
            visual_manifest=cmd_evidence_visual_manifest,
        ),
    )

    register_gate_commands(
        sub,
        add_leaf,
        GateCommandHandlers(
            run=cmd_gate_run,
            advance=cmd_gate_advance,
            transition=cmd_gate_transition,
            report_render=cmd_gate_report_render,
            control_reports=cmd_gate_control_reports,
        ),
    )

    # Discovery + graphify stage commands (discovery-improvement-plan M2.1).
    register_graphify_commands(
        sub,
        add_leaf,
        GraphifyCommandHandlers(status=cmd_graphify_status),
    )

    # PRD stage commands (prd-improvement-plan M2.1)
    register_prd_commands(
        sub,
        add_leaf,
        PrdCommandHandlers(
            anti_pattern_scan=cmd_prd_anti_pattern_scan,
            domain_model_lint=cmd_prd_domain_model_lint,
            agent_cap_eval=cmd_prd_agent_cap_eval,
        ),
    )

    register_discovery_commands(
        sub,
        add_leaf,
        DiscoveryCommandHandlers(
            skip=cmd_discovery_skip,
            summary=cmd_discovery_summary,
            check_dependency_trigger=cmd_discovery_check_dependency_trigger,
            agent_eng_eval=cmd_discovery_agent_eng_eval,
        ),
    )

    # Stage-4 design lane CLIs (M2.1).
    register_solution_commands(
        sub,
        add_leaf,
        SolutionCommandHandlers(
            decision_scan=cmd_solution_decision_scan,
            lane_action_validate=cmd_solution_lane_action_validate,
        ),
    )

    register_interaction_commands(
        sub,
        add_leaf,
        InteractionCommandHandlers(
            check_ui_trigger=cmd_interaction_check_ui_trigger,
            spec_check=cmd_interaction_spec_check,
            ux_quality_check=cmd_interaction_ux_quality_check,
            visual_coverage_check=cmd_interaction_visual_coverage_check,
            trace_coverage_check=cmd_interaction_trace_coverage_check,
            prototype_check=cmd_interaction_prototype_check,
            project=cmd_interaction_project,
            resolve_feedback=cmd_interaction_resolve_feedback,
            locator_check=cmd_interaction_locator_check,
            feedback_sync_check=cmd_interaction_feedback_sync_check,
            gate_run=cmd_interaction_gate_run,
        ),
    )

    register_prototype_as_frontend_commands(
        sub,
        add_leaf,
        PrototypeAsFrontendCommandHandlers(
            changeset_check=cmd_prototype_as_frontend_changeset_check,
            path_check=cmd_prototype_as_frontend_path_check,
            drift_check=cmd_prototype_as_frontend_drift_check,
            gate_run=cmd_prototype_as_frontend_gate_run,
        ),
    )

    register_alignment_commands(
        sub,
        add_leaf,
        AlignmentCommandHandlers(check=cmd_alignment_check),
    )

    register_tech_design_commands(
        sub,
        add_leaf,
        TechDesignCommandHandlers(
            check_dep_impact_trigger=cmd_tech_design_check_dep_impact_trigger,
            check_capability_trigger=cmd_tech_design_check_capability_trigger,
        ),
    )

    register_lint_commands(
        sub,
        add_leaf,
        LintCommandHandlers(
            runtime=cmd_lint_runtime,
            graph=cmd_lint_graph,
            project=cmd_lint_project,
        ),
    )

    # PT-CLI-EXTEND-04: harness acceptance record — CLI Bridge shim for
    # acceptance_decision typed action (DATA-11; INV-10 evidence gap blocker).
    register_acceptance_commands(
        sub,
        add_leaf,
        AcceptanceCommandHandlers(record=cmd_acceptance_record),
    )

    register_project_context_commands(
        sub,
        add_leaf,
        ProjectContextCommandHandlers(
            add_lesson=cmd_project_context_add_lesson,
            drift_scan=cmd_project_context_drift_scan,
            lint=cmd_project_context_lint,
        ),
    )

    register_retrospective_commands(
        sub,
        add_leaf,
        RetrospectiveCommandHandlers(
            harness_gap_init=cmd_retrospective_harness_gap_init,
            harness_gap_emit=cmd_retrospective_harness_gap_emit,
        ),
    )

    register_harness_gap_commands(
        sub,
        add_leaf,
        HarnessGapCommandHandlers(pattern_scan=cmd_harness_gap_pattern_scan),
    )

    register_agent_eval_commands(
        sub,
        add_leaf,
        AgentEvalCommandHandlers(drift=cmd_agent_eval_drift),
    )

    # delivery-improvement-plan M2.1: delivery stage CLI.
    register_delivery_commands(
        sub,
        add_leaf,
        DeliveryCommandHandlers(
            summarize=cmd_delivery_summarize,
            compute_follow_ups=cmd_delivery_compute_follow_ups,
            check_followups=cmd_delivery_check_followups,
            compute_conclusion=cmd_delivery_compute_conclusion,
            handoff=cmd_delivery_handoff,
            agent_capability_status=cmd_delivery_agent_capability_status,
        ),
    )

    # finishing-branch stage commands (M2.1)
    register_finishing_branch_commands(
        sub,
        add_leaf,
        FinishingBranchCommandHandlers(
            status=cmd_finishing_branch_status,
            detect_test_cmd=cmd_finishing_branch_detect_test_cmd,
            run_tests=cmd_finishing_branch_run_tests,
            readiness=cmd_finishing_branch_readiness,
            options=cmd_finishing_branch_options,
            pr_body=cmd_finishing_branch_pr_body,
            execute=cmd_finishing_branch_execute,
            cleanup=cmd_finishing_branch_cleanup,
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
