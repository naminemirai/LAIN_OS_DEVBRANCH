# In Progress

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

- Inventory the integrated Phase-1 GUI/runtime/transport acceptance already covered and map only the missing adversarial cases.

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
