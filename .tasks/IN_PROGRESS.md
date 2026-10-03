# In Progress

## TASK-005: Implement persistent PlannerProfile selection
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-1, planner-runtime
**Updated:** 2026-10-03

### Goal

Create the provider-neutral Android planner profile store required to select Demo, Cloud, or Local intelligence without placing credentials in profile state.

### Scope

- Define native `PlannerProfile` persistence for profile ID/name, mode, protocol, base URL, model, opaque credential reference, timeout, response-size bound, response mode, and supported local-network policy fields.
- Keep raw credentials exclusively in the existing Keystore-backed `SecretStore`.
- Persist the active profile across process/app restart.
- Convert the selected profile into the existing trusted `PlannerBinding` captured when a new agent session starts.
- Settings changes affect future sessions only; existing sessions remain pinned to their original binding.

### Dependencies

- Existing `PlannerBinding` validation/session-pinning groundwork on main.
- Existing TASK-002 Keystore-backed `SecretStore`.
- No hard dependency on TASK-003 transport integration; do not duplicate or modify native transport work owned by PR #8.

### Plan

- Add the smallest native profile model/store and validation boundary.
- Make Demo the safe default when no user profile is selected.
- Store only opaque credential references.
- Add active-profile CRUD/selection operations needed by the later bridge/UI.
- Prove restart persistence and session pinning with focused tests.

### Acceptance

- Demo, Cloud, and Local profiles validate under one provider-neutral schema.
- Invalid endpoint/model/profile input fails closed.
- Restart preserves profiles and active selection.
- Raw credentials never enter profile files, Binder/IPC responses, Python checkpoints, audit, logs, or exported settings.
- A session created under profile A remains bound to A after the active setting changes to B.

### Verification

- Focused profile-store/validation tests.
- Restart/persistence and profile-selection tests.
- Session-pinning regression against existing `PlannerBinding`.
- Canonical portable verification and Android test/build gates when implementation is integrated.

### Expected result

LAIN_OS has a durable, non-secret source of planner identity/configuration that the runtime bridge and settings UI can consume without weakening authority boundaries.

### Evidence / projection basis

- Code search on `main@06ead233185f3e90e2f979bd798aa6d407e22f1c` finds `PlannerBinding` and session pinning but no `PlannerProfile`/profile-store implementation.
- `docs/PLUGGABLE_MODEL_RUNTIME.md` defines P2-02/R1.2 as a prerequisite for the runtime bridge.
- This task unlocks TASK-006 while PR #8 completes transport integration.

---
