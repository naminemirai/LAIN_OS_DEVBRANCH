# In Progress

## TASK-006: Wire profile-selected planner runtime bridge
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-1, planner-runtime
**Updated:** 2026-10-03

### Goal

Replace the Android embedded runtime's hardcoded `DemoPlanner` construction with a profile-selected planner factory/bridge that can use Demo, Cloud, or Local model responses while preserving the trusted LAIN execution path.

### Scope

- Add the smallest Android/Python planner bridge over the native bounded transport.
- Select planner implementation from the session's pinned `PlannerBinding`.
- Keep credentials and HTTP ownership native; Python receives only bounded model response material and non-secret provider identity.
- Feed model output through the existing `AgentPlanningService`.
- Propagate Android Stop/cancellation through transport/controller without granting the bridge execution authority.
- Preserve Demo as a complete offline fallback mode chosen explicitly by profile, never as an automatic cloud/local fallback.

### Dependencies

- TASK-003 integrated: bounded native planner transport.
- TASK-005 complete: persistent profile selection and binding construction.

### Plan

- Define a narrow bridge contract from the existing native transport to an `AgentPlanner` implementation.
- Replace hardcoded `AgentPlanningService(DemoPlanner(...))` construction in the Android app runtime with a planner factory keyed by the pinned binding.
- Keep trusted IDs, validation, policy, approval, executor, verification, audit, and budgets unchanged.
- Add deterministic fake-transport tests for Demo/Cloud/Local and cancellation.

### Acceptance

- Demo continues to work fully offline.
- Cloud and Local bindings can each produce a valid `AgentPlannerDecision`.
- Invalid provider/model output still fails closed in existing planning validation.
- Local failure never falls back to Cloud.
- No bridge method can authorize or execute a capability directly.
- Stop/cancellation prevents later actions from being scheduled after cancellation settles.
- Provider credentials are absent from Python durable state and bridge responses.

### Verification

- Focused Python planner-factory/bridge tests.
- Android bridge/instrumentation tests using an injected fake native transport.
- Cancellation/no-fallback regressions.
- Canonical portable verification plus Android API matrix.

### Expected result

The installed Android runtime can obtain real model decisions from the selected Cloud/Local profile while every action still traverses LAIN's existing trusted validation/policy/execution/verification/audit pipeline.

### Evidence / projection basis

- `lain/app/control.py` on current main still constructs `AgentPlanningService(DemoPlanner(workspace), ...)`.
- PR #8 supplies the bounded native transport seam.
- The 1.0 roadmap names R1.5/P2-05 as the critical bridge before planner settings can become functional.

---
