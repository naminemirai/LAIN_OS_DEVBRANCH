# Next

## TASK-016: Define durable workflow persistence model
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-3, workflow, persistence
**Updated:** 2026-10-03

### Goal

Introduce the versioned durable workflow state model that Phase 3 can build on without weakening the existing trusted executor or replay protections.

### Scope

- Define a workflow schema covering stable ID, dependencies, status, restricted role, allowed capability families, artifact references/hashes, acceptance checks, attempted operations, budgets, retries, provider job IDs, deadlines, error/recovery state, revision, approvals, and reconciliation state.
- Implement atomic local persistence with strict validation, schema versioning, and fail-closed corrupt-state handling.
- Define migration boundaries for compatible future schema revisions.
- Preserve existing agent sessions and trusted action execution as lower-level primitives; do not replace policy/executor/verification/audit.
- Do not implement DAG scheduling, artifact storage, specialist execution, or external-effect retry in this task.

### Dependencies

- TASK-015 complete: Phase-2 voice acceptance gate.
- Existing atomic file/session-store patterns and audit/error models should be reused where appropriate.

### Plan

- Inventory current durable session/checkpoint patterns for reuse.
- Define the smallest versioned workflow record/state schema needed by R3.2-R3.8.
- Add strict serialization/deserialization and atomic write/read behavior.
- Fail closed on unknown versions, malformed fields, invalid transitions, duplicate IDs, or corrupt persisted state.
- Add migration hook structure without speculative migrations.
- Add focused persistence/corruption/version tests.

### Acceptance

- A valid workflow round-trips through durable storage without losing authoritative state.
- Unknown schema versions and corrupt state fail explicitly without silent reset or replay.
- Atomic writes cannot expose a partially written valid-looking workflow.
- Stable IDs/revisions/dependencies/status and reconciliation state are preserved exactly.
- No workflow record can grant capabilities or bypass policy/approval merely by persisted content.
- Existing agent/session persistence remains compatible and independently authoritative for its current scope.

### Verification

- Focused schema/round-trip/corruption/version tests.
- Atomic-write interruption/recovery tests where deterministic.
- Negative tests for duplicate IDs, invalid dependency references, invalid transitions, malformed budgets/approvals/reconciliation fields.
- Canonical portable verification after implementation.
- Fresh architecture review before integrating scheduler work.

### Expected result

LAIN_OS gains a strict durable workflow-state foundation that can support dependency scheduling, artifacts, revisions, long waits, and reconciliation without inventing those higher layers prematurely.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R3.1 Workflow persistence model as the first Phase-3 work package.
- No current TaskPlanner task, open issue, or open PR represents R3.1.

### Projection basis

- Every later Phase-3 work package depends on a stable persisted workflow identity/state contract; defining it first prevents scheduler/artifact/revision layers from inventing incompatible durable state.

### Risks / unknowns

- Migration semantics beyond the initial version are intentionally deferred until a real second schema exists.
- Cross-process locking needs should follow actual runtime topology rather than speculative multi-writer support.

---

## TASK-015: Close Phase-2 voice acceptance gate
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-2, voice, acceptance
**Updated:** 2026-10-03

### Goal

Prove the integrated voice conversation stack is safe, interruptible, recoverable, and truthfully observable before Phase 2 exits.

### Scope

- Exercise the integrated R2.1-R2.6 path across microphone/transcript, turn management, synthesis/playback, barge-in, and progress narration.
- Cover permission denied/revoked, provider unavailable/offline, rotation/rebind, interruption, Stop talking vs Stop task, and low-confidence consequential commands.
- Measure interruption-to-playback-stop and trusted pause/cancel latency only on a declared reference device when hardware is actually exercised.
- Verify typed fallback and that speech/TTS failure never becomes task failure or fabricated completion.
- Preserve the trusted policy/approval/execution/verification/audit path.
- Do not broaden into Phase-3 workflow/DAG features.

### Dependencies

- TASK-009 through TASK-014 complete.
- TASK-008 complete as the Phase-1 planner foundation.

### Plan

- Build a reproducible end-to-end voice acceptance matrix over the integrated components.
- Use deterministic fakes/emulator instrumentation for logic/failure cases and keep hardware-only evidence separate.
- Add negative authority tests for partial/low-confidence speech, echo, playback failure, and TTS outage.
- Exercise independent Stop talking and Stop task paths.
- Record latency only from actual declared reference-device runs.
- Run canonical portable/Android verification and fresh review.

### Acceptance

- User can start a voice session, speak a normal goal, hear a response, interrupt it, revise the request, and stop the underlying task independently of playback.
- Permission/provider/lifecycle failures are explicit and cannot create hidden listening or fabricated task state.
- Partial or low-confidence consequential speech cannot authorize work outside the final-turn/approval path.
- Typed fallback remains complete.
- TTS/playback failure does not fail an otherwise healthy task.
- Emulator evidence is never promoted to reference-device latency evidence.

### Verification

- Integrated Android voice acceptance/instrumentation suite.
- Negative authority/failure-mode matrix.
- Canonical portable verification and Android API matrix.
- Relevant secret/audio-retention inspection.
- Hardware latency measurement only if a reference device is actually exercised.
- Fresh whole-diff review.

### Expected result

Phase 2 has a reproducible exit gate demonstrating a safe voice-first interface with truthful interruption, recovery, fallback, and authority semantics.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R2.7 Voice acceptance and the Phase-2 exit gate.
- No exact current TaskPlanner task, open issue, or open PR represents R2.7.

### Projection basis

- This gate prevents unresolved audio/authority/lifecycle defects from propagating into Phase-3 durable workflow work.

### Risks / unknowns

- Reference-device execution may be unavailable in CI; such latency evidence must remain explicitly UNVERIFIED.
- Live provider checks are supplementary; deterministic CI evidence remains the reproducible gate.

---

## TASK-014: Implement voice progress narration
**Priority:** P2 | **Tags:** overseer-assigned, developer, phase-2, voice, progress
**Updated:** 2026-10-03

### Goal

Add bounded spoken progress events that narrate useful task state without turning speech delivery into durable workflow truth or making TTS availability a task dependency.

### Scope

- Define short progress-narration events derived from trusted durable task/session state.
- Keep spoken progress separate from durable workflow/task state and planner assertions.
- Route progress narration through the provider-neutral synthesis/playback boundaries from TASK-009/TASK-012.
- Coalesce/rate-limit repetitive progress speech so narration cannot starve work or create unbounded provider calls.
- Allow playback interruption through TASK-013 without cancelling the task.
- Ensure speech/TTS failure never marks the underlying task failed or complete.
- Preserve visual/text progress as the authoritative fallback.
- Do not implement Phase-3 workflow DAG state, publication narration, or provider-specific TTS behavior.

### Dependencies

- TASK-009 complete: speech provider interfaces.
- TASK-011 complete: turn semantics.
- TASK-012 complete: cancellable playback.
- TASK-013 complete: barge-in/echo protection.

### Plan

- Define a minimal progress-event schema sourced only from trusted runtime state.
- Add bounded event-to-utterance formatting with coalescing/rate limits.
- Send narration through synthesis/playback as a non-authoritative side channel.
- Make synthesis/playback errors local to narration and preserve underlying task state.
- Add deterministic tests for event provenance, coalescing, failure isolation, and interruption behavior.

### Acceptance

- Spoken progress is generated only from trusted current task/session state.
- Narration cannot change task status, grant approval, authorize capabilities, or fabricate completion.
- TTS/provider/playback failure leaves the task running or settled exactly as before.
- Repetitive progress events are bounded/coalesced.
- User barge-in can stop progress speech without stopping the task.
- Visual/text state remains available and authoritative when speech is unavailable.
- No raw provider credential enters progress events or narration artifacts.

### Verification

- Focused progress-event/provenance/coalescing tests.
- Negative tests proving narration failure does not alter task state.
- Regression proving spoken “complete” text cannot itself mark work complete.
- Android integration coverage for narration playback/interruption.
- Canonical verification after implementation.

### Expected result

LAIN_OS can speak concise progress while work continues, with speech treated as a fallible presentation channel rather than a source of execution truth.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R2.6 Voice progress narration: progress events separate from durable workflow state, speech failure never equals task failure, and tasks continue if TTS is unavailable.
- No current TaskPlanner task, open issue, or open PR represents R2.6.

### Projection basis

- Progress narration is the last functional voice slice before R2.7 acceptance and therefore should reuse already-stable turn/playback/barge-in contracts rather than introduce a new authority path.
- Failure isolation is necessary before voice acceptance can truthfully test provider outages and interruption.

### Risks / unknowns

- Exact wording/verbosity policy is presentation-level and should remain adjustable without changing durable state contracts.
- Aggregate speech-provider cost budgets may be refined later with Phase-3 workflow budgets; this task needs only local bounded/rate-limited behavior.
- Reference-device latency and full voice-session acceptance belong to R2.7.

---


## TASK-013: Implement voice barge-in and echo protection
**Priority:** P2 | **Tags:** overseer-assigned, developer, phase-2, voice, safety
**Updated:** 2026-10-03

### Goal

Allow user speech to interrupt active synthesis without confusing synthesized audio or partial recognition with authoritative user intent.

### Scope

- Detect user speech while synthesis/playback is active and stop or duck playback promptly.
- Keep “Stop talking” independent from “Stop task”.
- Prevent synthesized speech from being re-ingested as a user command.
- Ensure partial/interim recognition cannot authorize consequential actions.
- Preserve final-turn authority through TASK-011 turn-manager semantics.
- Do not implement provider-specific echo-cancellation SDKs, wake words, progress narration, or Phase-3 workflow semantics.

### Dependencies

- TASK-010 complete: microphone lifecycle.
- TASK-011 complete: authoritative turn manager.
- TASK-012 complete: cancellable playback.

### Plan

- Define the smallest barge-in coordinator across microphone, turn, and playback state.
- Stop/duck playback on confirmed user speech onset without cancelling task state.
- Gate recognized input so synthesized output and partial transcripts cannot enter the authoritative turn path.
- Add deterministic regressions for echo-loop rejection, partial-recognition non-authority, and Stop-talking vs Stop-task separation.
- Measure interruption-to-playback-stop timing in controlled tests; reserve reference-device acceptance for TASK-015/R2.7.

### Acceptance

- User speech during playback stops or ducks synthesis without cancelling the underlying task.
- Synthesized speech cannot become a user turn or capability request.
- Partial recognition cannot grant approval or authorize consequential work.
- Only final accepted user turns can enter the authoritative task-facing pipeline.
- Stop talking and Stop task remain independently observable operations.
- Failure of echo/barge-in handling never fabricates task completion.

### Verification

- Focused coordinator tests for playback interruption and authority separation.
- Negative echo-loop and partial-transcript authorization tests.
- Android integration/instrumentation around simultaneous capture/playback.
- Controlled interruption latency measurement without claiming physical-device acceptance unless actually run.
- Canonical verification after implementation.

### Expected result

LAIN_OS supports safe conversational interruption while keeping audio feedback, partial speech, task cancellation, and user authority sharply separated.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R2.5 barge-in and echo protection immediately after speech playback.
- No current TaskPlanner task, open issue, or open PR represents R2.5.

### Projection basis

- R2.5 is required before voice progress narration and the Phase-2 acceptance gate because interruption semantics must be stable before spoken progress can coexist with user speech.

### Risks / unknowns

- Device-level acoustic echo cancellation varies by hardware; software authority filtering must remain correct even if acoustic suppression is imperfect.
- Reference-device latency belongs to the Phase-2 acceptance gate, not this task.

---

## TASK-012: Implement cancellable speech playback
**Priority:** P2 | **Tags:** overseer-assigned, developer, phase-2, voice, android-audio
**Updated:** 2026-10-03

### Goal

Add bounded Android speech playback for synthesized responses with explicit audio-focus ownership, truthful playback state, and cancellation independent from underlying task cancellation.

### Scope

- Consume synthesis results from the TASK-009 provider-neutral speech interface.
- Implement start/stop playback with surfaced playback state.
- Acquire/release Android audio focus deterministically and handle focus loss/ducking safely.
- Provide explicit TTS/playback cancellation that does not cancel the underlying LAIN task.
- Keep synthesized output non-authoritative: playback cannot create user turns, approvals, or capability requests.
- Preserve typed/visual result delivery when playback fails.
- Do not implement microphone capture, barge-in/echo protection, provider-specific TTS SDKs, or workflow progress narration in this task.

### Dependencies

- TASK-009 complete: bounded speech provider interfaces.
- TASK-011 complete: turn manager distinguishes conversational turns from task state.
- Existing Android lifecycle/rebind patterns remain authoritative.

### Plan

- Define the smallest playback controller/state model around synthesized audio artifacts/streams.
- Add deterministic audio-focus acquisition, loss, duck, stop, and teardown paths.
- Keep “Stop talking” separate from “Stop task” in API/state semantics.
- Surface playback state to the Android UI boundary.
- Add focused JVM/instrumentation tests for start/stop/focus-loss/cancellation/lifecycle teardown.

### Acceptance

- Playback starts only from an explicit synthesized-response request.
- Audio focus is released on completion, cancellation, focus loss, and lifecycle teardown.
- “Stop talking” stops playback without cancelling or falsifying the underlying task.
- Playback failure leaves durable task state unchanged and preserves typed/visual output.
- Synthesized audio cannot be routed as a user command through this layer.
- Playback state is truthful and visible to the UI.
- No raw speech-provider credential enters playback state or artifacts.

### Verification

- Focused playback-state/audio-focus tests.
- Android instrumentation for start/stop, focus loss/ducking, cancellation, rotation/rebind, and teardown.
- Negative test proving playback cancellation does not alter task status.
- Negative inspection proving synthesized output cannot directly enter the authoritative turn pipeline.
- Canonical Android build/lint/instrumentation gates after implementation.

### Expected result

LAIN_OS can speak responses through a cancellable Android playback boundary while keeping audio lifecycle, user-turn authority, and task cancellation cleanly separated.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R2.4 Speech playback: audio focus, start/stop/duck, TTS cancellation, and playback state surfaced to UI.
- No current TaskPlanner task, open issue, or open PR represents R2.4.

### Projection basis

- A stable playback boundary is required before R2.5 barge-in/echo protection can safely interrupt speech without conflating “stop talking” with “stop task.”
- Separating playback state from task state prevents speech-provider or audio failures from becoming false task failures.

### Risks / unknowns

- Exact Android playback primitive and streaming buffer strategy may depend on the synthesis adapter contract; keep the controller bounded and provider-neutral.
- Reference-device latency belongs to R2.7 acceptance, not this task.
- Echo suppression and synthesized-speech command filtering belong to R2.5 and must not be pre-built here.

---

## TASK-011: Implement bounded voice turn manager
**Priority:** P2 | **Tags:** overseer-assigned, developer, phase-2, voice, conversation
**Updated:** 2026-10-03

### Goal

Add the durable conversation-turn coordination layer that converts final transcripts or typed revisions into ordered task-facing turns without allowing partial speech or ambiguous references to authorize consequential work.

### Scope

- Assign monotonic turn IDs for each accepted user turn.
- Keep partial/interim transcripts separate from final accepted transcripts.
- Track an explicit active-task reference for conversational follow-ups.
- Route clear revisions to the referenced task/workflow without mutating already-approved consequential payloads in place.
- Surface ambiguous referents as a clarification-required state rather than guessing.
- Preserve typed input as an equivalent complete turn source.
- Do not implement microphone capture, speech playback, barge-in, workflow DAG semantics, or provider-specific speech logic in this task.

### Dependencies

- TASK-009 complete: bounded speech provider interfaces.
- TASK-010 complete: Android microphone lifecycle producing final/partial capture results.
- Existing durable agent-session identifiers and approval semantics remain authoritative.

### Plan

- Define the smallest turn record/state model with monotonic IDs and explicit source/finality fields.
- Add active-task reference tracking without duplicating durable workflow authority.
- Route only final accepted turns into task/planner input; partial transcripts remain non-authoritative UI state.
- Add explicit ambiguous-reference and revision-routing outcomes.
- Add deterministic tests for turn ordering, partial/final separation, active-task reference, ambiguity, and revision routing.

### Acceptance

- Accepted turns receive strictly monotonic IDs.
- Partial transcripts cannot start work, grant approval, or alter durable task state.
- Final transcripts and typed messages enter the same bounded turn pipeline.
- Follow-up references resolve only when an active target is unambiguous.
- Ambiguous referents require clarification and execute nothing.
- Revision routing preserves prior approvals/effects and creates a new revision intent rather than silently mutating an approved consequential payload.
- Turn state contains no raw provider credential or hidden capability authority.

### Verification

- Focused unit tests for ordering, finality, reference resolution, ambiguity, and revisions.
- Negative tests proving partial transcripts and ambiguous turns cannot trigger planner/executor work.
- Regression proving typed input follows the same turn contract.
- Canonical portable verification and Android integration checks after platform wiring.

### Expected result

LAIN_OS has a deterministic conversation-turn boundary that later playback, barge-in, and workflow features can consume without conflating speech fragments with authoritative user intent.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R2.3 Turn manager with monotonic turn IDs, final-vs-partial transcript separation, active-task reference, ambiguous referent clarification, and revision routing.
- No current TaskPlanner task, open issue, or open PR represents R2.3.

### Projection basis

- A stable turn boundary is required before speech playback/barge-in can safely distinguish conversational interruption from task cancellation or authorization.
- Explicit finality and reference semantics prevent later voice features from treating low-confidence/partial speech as consequential intent.

### Risks / unknowns

- Full workflow revision invalidation belongs to Phase 3; this task should expose revision intent/reference only, not pre-build the DAG scheduler.
- Multi-workflow targeting is beyond the current single-active-workflow 1.0 scope and should not broaden this contract.
- Low-confidence STT scoring may be provider-specific later; this task should depend on explicit finality/clarification semantics rather than a hard-coded confidence model.

---

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
