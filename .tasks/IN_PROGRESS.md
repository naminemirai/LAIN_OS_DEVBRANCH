# In Progress

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
