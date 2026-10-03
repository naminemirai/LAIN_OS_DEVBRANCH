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

## TASK-008: Close Phase-1 planner acceptance and adversarial gate
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-1, acceptance, adversarial
**Updated:** 2026-10-03

### Goal

Prove the installed Android planner runtime is safe, durable, and truthful across Demo, Cloud, and Local modes before Voice Conversation work begins.

### Scope

- Add end-to-end acceptance coverage spanning profile persistence, native transport, runtime bridge, settings selection, and trusted execution.
- Exercise Cloud and Local happy paths through the installed Android GUI/runtime using controlled test endpoints or injected equivalents appropriate to each layer.
- Cover DNS/unreachable, refused connection, TLS, 401/403, model/404, timeout/408, 429, 5xx, cancellation, oversized response, malformed JSON, schema-invalid model output, unknown capability, provider outage during session, local endpoint loss, missing credential, and no-cloud-fallback behavior.
- Verify restart/profile persistence and exact session pinning.
- Verify provider credentials are absent from profile files, Python checkpoints, Binder/IPC responses, audit, logs, crash-facing diagnostics, and exported settings.
- Preserve the existing trust boundary: model output must still traverse trusted validation, policy, approval, execution, verification, and audit.

### Dependencies

- TASK-005 complete: persistent PlannerProfile selection.
- TASK-006 complete: profile-selected planner runtime bridge.
- TASK-007 complete: Planner Settings and inert connection diagnostics.
- TASK-003 integrated: bounded native planner transport.

### Plan

- Build the smallest acceptance harness around the integrated Phase-1 implementation.
- Reuse existing deterministic fakes/emulator infrastructure where they truthfully exercise failure contracts; use Android instrumentation for platform/runtime behavior that JVM tests cannot establish.
- Add explicit negative assertions for secret leakage, fabricated completion, capability-authority bypass, and Local-to-Cloud fallback.
- Run canonical portable verification plus the Android API matrix.
- Record any physical-device-only acceptance debt separately; do not promote emulator evidence to hardware evidence.

### Acceptance

- Installed GUI can select Demo, Cloud, or Local planner mode and complete a typed natural-language request through the existing trusted action pipeline.
- Cloud and Local success paths produce validated planner decisions without changing authority semantics.
- Every required transport/provider failure maps to an explicit non-success state.
- Invalid or malicious planner output cannot execute an unknown/unauthorized capability.
- Provider outage or endpoint loss cannot fabricate progress or completion.
- Local mode never silently falls back to Cloud.
- Restart preserves profile selection and active sessions remain pinned to their original planner identity.
- Secret scan/inspection finds no raw provider credential in durable or returned LAIN artifacts.
- Existing canonical verification and Android emulator gates remain green or any failure is persisted as an explicit blocker.

### Verification

- Focused planner acceptance/adversarial test suite.
- Canonical `python scripts/verify.py`.
- Android build/lint/unit/instrumentation on supported API matrix.
- Fresh secret-leak scan of relevant persisted/runtime surfaces.
- Fresh whole-diff review before integration.
- Physical-device-only claims remain UNVERIFIED unless actually exercised on hardware.

### Expected result

Phase 1 has a reproducible acceptance gate demonstrating that real selectable planner intelligence works end to end without bypassing LAIN's local authority, secrecy, recovery, cancellation, or verification guarantees.

### Evidence / projection basis

- Current TaskPlanner covers R1.2/R1.5/R1.6 as TASK-005/006/007, but no task represents R1.7/P2-07.
- `docs/ROADMAP_1.0.md` explicitly requires a Planner acceptance and adversarial suite before Phase 1 exits.
- `docs/PLUGGABLE_MODEL_RUNTIME.md` defines P2-07 as end-to-end Android acceptance around planner modes and provider failures.
- Voice Conversation is sequenced after a stable planner phase, so this gate prevents carrying unresolved model-runtime trust defects into the next public interface.

### Risks / unknowns

- Some network/provider failure cases may require deterministic injected transports rather than live external services for reproducibility.
- Physical-device acceptance is distinct from emulator/instrumentation evidence and must remain labeled separately.
- If TASK-005/006/007 alter public seams, this task should adapt to the integrated contracts rather than freeze speculative test APIs.

---
