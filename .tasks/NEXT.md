# Next

## TASK-010: Implement Android microphone lifecycle
**Priority:** P2 | **Tags:** overseer-assigned, developer, phase-2, voice, android-audio
**Updated:** 2026-10-03

### Goal

Add the bounded Android microphone lifecycle required for user-started voice sessions, with explicit permission, visible recording state, cancellation, and rotation/background safety while preserving typed input as a complete fallback.

### Scope

- Implement microphone permission request/revocation handling for explicit user-started capture only.
- Add start/stop capture lifecycle with visible recording state.
- Define bounded audio capture ownership and cleanup across activity/service lifecycle transitions.
- Handle rotation, rebind, foreground/background transitions, and permission revocation without leaving hidden capture active.
- Produce bounded audio input suitable for the TASK-009 transcription interface without embedding provider-specific logic.
- Default to no raw audio retention beyond the active bounded request unless an explicit later feature requires durable audio.
- Do not implement speech provider SDKs, turn management, playback, barge-in, or always-listening/wake-word behavior.

### Dependencies

- TASK-009 complete: bounded speech provider interfaces.
- Existing Android runtime/service lifecycle and Stop/rebind patterns.
- Existing permission and UI-state conventions where reusable.

### Plan

- Inventory current Activity/RuntimeService lifecycle and permission patterns.
- Add the smallest microphone capture controller/state model with explicit start/stop ownership.
- Route capture output only through the provider-neutral transcription seam.
- Make rotation/rebind/background/revocation transitions fail closed and release microphone resources deterministically.
- Add focused JVM/instrumentation coverage for permission, lifecycle, and no-hidden-capture invariants.

### Acceptance

- Recording starts only after an explicit user action and granted microphone permission.
- Recording state is visibly surfaced while capture is active.
- Stop releases microphone resources and prevents further audio delivery after cancellation settles.
- Rotation/rebind preserves truthful visible state or terminates capture cleanly according to the chosen lifecycle contract.
- Permission revocation terminates capture and surfaces a recoverable non-success state.
- Background transitions cannot create a hidden always-listening state.
- Captured audio is bounded and not durably retained by default.
- Typed interaction remains fully usable when microphone permission is denied or capture fails.

### Verification

- Focused microphone controller/state tests.
- Android instrumentation for permission denied/granted/revoked, start/stop, rotation/rebind, and background transitions.
- Resource-release assertions after cancellation and lifecycle teardown.
- Negative inspection proving no default raw-audio persistence.
- Canonical Android build/lint/instrumentation gates after implementation.

### Expected result

LAIN_OS can explicitly capture bounded user speech on Android and hand it to the provider-neutral transcription layer without hidden listening, lifecycle leaks, or coupling microphone state to provider or capability authority.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R2.2 Android microphone lifecycle immediately after R2.1 speech provider interfaces.
- The Phase-2 feature list requires user-started microphone sessions, visible recording state, permission/revocation handling, background/rotation behavior, typed fallback, and no raw audio retention by default.
- No current TaskPlanner task, open issue, or open PR represents R2.2.

### Projection basis

- Stabilizing microphone ownership and lifecycle before turn management and playback prevents later voice features from inheriting hidden-capture, permission, or rotation defects.
- R2.2 is a direct dependency for R2.3 turn management and the Phase-2 installed voice-session exit gate.

### Risks / unknowns

- Exact Android audio API choice may depend on latency and device support; prefer the smallest platform primitive that satisfies lifecycle/cancellation requirements.
- Background behavior may require a deliberate foreground-service policy; do not broaden scope unless existing Android constraints make it necessary.
- Physical-device latency and OEM microphone behavior remain separate acceptance evidence from emulator instrumentation.

---

## TASK-009: Define bounded speech provider interfaces
**Priority:** P2 | **Tags:** overseer-assigned, developer, phase-2, voice, provider-contract
**Updated:** 2026-10-03

### Goal

Establish the provider-neutral speech contracts that Phase 2 can build on without coupling Android microphone/playback lifecycle or trusted task authority to any specific STT/TTS vendor.

### Scope

- Define bounded transcription request/result and synthesis request/result contracts.
- Include provider identity/provenance, explicit timeout/cancellation semantics, media format metadata, and bounded payload/duration fields needed by later Android adapters.
- Keep speech providers outside capability authorization, policy, approval, execution, verification, audit, and durable workflow authority.
- Preserve typed text as a complete fallback path.
- Define failure categories sufficient for unavailable provider, timeout, cancellation, malformed response, unsupported media, and bounded-resource rejection.
- Do not implement microphone capture, playback, provider SDKs, or vendor credentials in this task.

### Dependencies

- TASK-008 complete: Phase-1 planner acceptance/adversarial gate.
- Existing trusted session/controller contracts must remain authoritative.
- Existing secret-handling boundary remains unchanged for any future provider credential references.

### Plan

- Inventory existing voice/speech references and reusable cancellation/error patterns.
- Define the smallest provider-neutral speech request/result interfaces and error model.
- Specify cancellation/timeout ownership and provenance fields without granting provider-side execution authority.
- Add deterministic contract tests for valid, malformed, cancelled, timed-out, and oversized inputs/results.
- Document the seam expected by later Android microphone lifecycle and playback tasks without pre-implementing those layers.

### Acceptance

- Transcription and synthesis each have explicit provider-neutral request/result contracts.
- Contracts carry enough format/provenance metadata for later Android adapters without embedding vendor-specific fields.
- Cancellation and timeout produce explicit non-success outcomes.
- Oversized or malformed provider data fails closed.
- Speech provider output cannot authorize capabilities, approve consequential actions, or mutate durable task state directly.
- Typed interaction remains independent of speech-provider availability.
- No raw provider credential is introduced into speech request/result payloads or durable artifacts.

### Verification

- Focused unit tests for request/result validation, bounds, cancellation, timeout, and malformed provider data.
- Static inspection confirming no capability/policy/executor authority is exposed through the speech interface.
- Canonical portable verification after implementation.
- Android build remains a downstream verification requirement when the interface is wired into platform adapters.

### Expected result

Phase 2 has a stable, bounded speech-provider seam that can support replaceable STT/TTS adapters while preserving LAIN_OS authority boundaries and allowing microphone, turn-management, and playback work to proceed independently.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines Phase 2 Voice Conversation and explicitly lists R2.1 Speech provider interfaces as the first work package.
- The 1.0 dependency graph sequences Phase 2 after the Phase-1 planner runtime gate.
- No current TaskPlanner task, open issue, or open PR represents R2.1.

### Projection basis

- Stabilizing speech request/result, cancellation, timeout, provenance, and failure contracts before microphone/playback integration reduces cross-module churn across R2.2-R2.6.
- This interface is a necessary dependency seam for replaceable speech providers and the voice-first 1.0 release outcome.

### Risks / unknowns

- Concrete codec/container choices may need adjustment when Android capture/playback constraints are implemented; keep the initial interface minimal and extensible rather than provider-specific.
- Streaming/partial-transcript support may require a later compatible extension; do not over-specify it before turn-manager requirements are implemented.
- Provider credential storage/selection may share later settings infrastructure, but this task must not invent that UI or persistence prematurely.

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
