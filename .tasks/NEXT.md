# Next

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

## TASK-007: Build Planner Settings and inert connection diagnostics
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-1, android-ui
**Updated:** 2026-10-03

### Goal

Expose safe user control of Demo, Cloud, and Local planner profiles in the Android GUI and make the active source of intelligence visible.

### Scope

- Add Planner settings for create/edit/delete/select profile.
- Provide mode, endpoint, model, timeout/bounds, and credential save/replace/remove controls appropriate to each mode.
- Never reveal a stored credential after save.
- Add bounded `Test Connection` diagnostics that create no agent session and execute no capability.
- Show active provider/model in the Workbench.
- Surface structured recovery states for authentication, model, TLS, timeout, unreachable, unsupported response, and missing credential failures.

### Dependencies

- TASK-005 complete: profile persistence.
- TASK-006 complete: profile-selected bridge/runtime factory.
- Existing TASK-002 SecretStore and TASK-003 native transport.

### Plan

- Add the smallest settings surface around the established profile/secret APIs.
- Wire credential-state controls to opaque refs only.
- Implement Test Connection through a diagnostic-only transport path.
- Display active planner identity in Workbench without leaking secrets.
- Add restart/UI-state and failure-state coverage.

### Acceptance

- User can select Demo/Cloud/Local and create/edit/select/delete profiles.
- Settings survive process/app restart.
- Credential state is visible only as saved/missing/replace/remove; raw secret is never rendered or returned.
- Test Connection cannot create a session, execute a capability, modify filesystem/device state, or bypass trusted planning validation.
- Workbench clearly identifies the selected provider/model.
- Structured failure messages correspond to transport/profile error states.

### Verification

- Android UI/instrumentation coverage for profile lifecycle and restart.
- Test Connection side-effect-negative tests.
- Secret-leak regression over UI text, IPC results, profile files, logs, audit, and checkpoints.
- Canonical Android build/lint/instrumentation gates.

### Expected result

A user can configure and visibly select real planner intelligence from the Android app, diagnose the endpoint safely, and return to the Workbench knowing exactly which planner source will be used.

### Evidence / projection basis

- No implemented settings/profile UI is found on current main; `Test Connection` exists only in planning documentation.
- R1.6/P2-06 is the direct dependency after the runtime bridge and is required for the Phase-1 installed-GUI exit gate.

---
