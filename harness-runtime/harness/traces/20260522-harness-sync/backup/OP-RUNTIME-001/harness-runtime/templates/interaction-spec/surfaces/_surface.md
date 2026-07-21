# Surface: {{surface_id}} — {{surface_name}}

## Identity

| Field | Value |
|-------|-------|
| Surface ID | {{surface_id}} |
| Bounded Context / Module | {{bounded_context}} |
| Navigation Node | {{navigation_node}} |
| Operation | create_surface / modify_surface / extend_surface / retire_surface |
| Baseline Ref | {{baseline_ref_or_none}} |

## Purpose

{{surface_purpose}}

## Trace

| Ref Type | Refs |
|----------|------|
| AC / Scenario | {{ac_or_scenario_refs}} |
| Domain Objects | {{domain_object_refs}} |
| Domain Actions | {{domain_action_refs}} |
| Spec Requirements | {{spec_requirement_refs}} |

## Semantic Layout

| Region | Slot | Content / Data | Source | State Sensitivity |
|--------|------|----------------|--------|-------------------|
| {{region}} | {{slot}} | {{content}} | {{source}} | {{states}} |

## States

| State | Visible Content | Available Actions | Disabled Actions | Exit Condition |
|-------|-----------------|-------------------|------------------|----------------|
| STATE-{{id}} | {{content}} | {{actions}} | {{disabled}} | {{exit_condition}} |

## Interactions

| Trigger | Input Method | Guard | Result | Feedback | Trace |
|---------|--------------|-------|--------|----------|-------|
| {{trigger}} | mouse / keyboard / touch | {{guard}} | {{result}} | {{feedback}} | {{trace_ref}} |

## Accessibility

| Requirement | Design |
|-------------|--------|
| Focus order | {{focus_order}} |
| Accessible names | {{accessible_names}} |
| Keyboard shortcuts | {{keyboard_actions}} |
| Error announcement | {{error_announcement}} |

