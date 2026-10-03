# Next

## TASK-029: Implement real video inspection
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-4, media, inspection
**Updated:** 2026-10-03

### Goal

Independently inspect the actual renderer output and promote it to a verified video artifact only when the file exists, decodes, contains the required streams, matches declared dimensions and duration bounds, and has a recorded content hash.

### Scope

- Inspect only a completed TASK-028 output resolved through the immutable artifact workspace and current workflow revision.
- Use a bounded Android-compatible media probe/decoder path; do not trust filename extensions, planner claims, renderer exit status, or metadata sidecars as verification.
- Verify file existence/readability, container decode, at least one video stream, expected audio presence, pixel dimensions, duration tolerance, byte bounds, and full-file hash.
- Bind inspection evidence to the exact render attempt, timeline revision, renderer identity, input artifact hashes, output artifact identity, and workflow revision.
- Persist explicit inspection success/failure without mutating the rendered bytes or granting preview/export/publication authority.
- Do not implement rendering, preview/export UI, sharing, publication, cloud media generation, or generic file probing.

### Dependencies

- TASK-028 complete: a bounded renderer produces a candidate video artifact.
- TASK-025 complete: media artifact schema and immutable identity.
- TASK-018, TASK-020, TASK-023, and TASK-024 complete: immutable artifacts, revision invalidation, aggregate budgets, and durable-workflow acceptance.

### Plan

- Define a closed inspection request/result contract over immutable video artifact references.
- Select or reuse the smallest Android-compatible probe/decoder surface that exposes stream, dimension, duration, and decode evidence under cancellation and resource bounds.
- Compute the candidate file hash independently and compare all observed properties with the render/timeline contract.
- Promote verification atomically only after every required check passes for the current revision.
- Add real-fixture, malformed-container, corrupt/truncated, missing-stream, metadata-mismatch, stale-revision, cancellation, timeout, and duplicate-resume coverage.

### Acceptance

- A valid TASK-028 output is independently opened and decoded, with observed video stream, expected audio stream, dimensions, duration, byte size, and content hash recorded.
- Renderer exit success, file presence alone, extension/MIME claims, or sidecar metadata cannot produce inspection success.
- Missing, unreadable, empty, truncated, corrupt, oversized, unsupported-codec, no-video, unexpected-no-audio, wrong-dimension, duration-mismatch, or hash-mismatch output fails closed.
- Inspection evidence is bound to the exact candidate artifact, render attempt, timeline/input hashes, tool identity/version, and current workflow revision.
- Cancellation, timeout, process death, or stale revision cannot promote a candidate to verified state.
- Resume reuses only matching durable completed evidence or reruns inspection; it never guesses success from a partial record.
- Inspection exposes no arbitrary path, command, shell, preview, export, sharing, or publication surface.

### Verification

- Contract tests using one real valid offline video fixture with asserted streams, dimensions, duration tolerance, byte size, and hash.
- Corrupt, truncated, malformed-container, unsupported-codec, missing-audio/video, wrong-dimension/duration/hash, hostile-path, and oversized-file negatives.
- Cancellation, timeout, stale-revision, process-restart, partial-record, and duplicate-resume tests.
- Canonical portable verification, Android build/lint/tests, and supported emulator/device decode evidence kept explicitly separated.
- Fresh architecture/security review of path handling, resource bounds, evidence atomicity, and authority boundaries.

### Expected result

Phase 4 can distinguish a genuinely decodable, contract-matching video from a merely produced file and expose durable inspection evidence for preview and the offline golden fixture without widening execution or publication authority.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R4.5 Video inspection immediately after R4.4 Renderer and explicitly requires existence, decode, video/audio streams, dimensions, duration, and file hash.
- Current TaskPlanner, open issues, and open PRs end Phase-4 planning at TASK-028/R4.4; no current repository-native record represents R4.5.

### Projection basis

- R4.6 preview/export and R4.7 offline golden fixture need independently verified media properties; treating renderer completion as inspection would make later acceptance circular.

### Risks / unknowns

- Android decoder/container behavior can differ by API level and device codec availability; evidence must label platform/API/device and keep portable structural checks distinct.
- Full decode may be resource-expensive; bounded sampling versus full-stream validation must be chosen explicitly without overstating assurance.
- The inspection tool may share libraries with the renderer; independent observation still requires a separate verification path and result contract.

---

## TASK-028: Integrate a bounded Android-capable video renderer
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-4, media, renderer
**Updated:** 2026-10-03

### Goal

Select and integrate the smallest Android-compatible rendering toolchain that turns a validated TASK-027 timeline plus immutable media artifacts into one deterministic video artifact under trusted bounds, cancellation, and explicit failure semantics.

### Scope

- Evaluate only renderer options that can be packaged and licensed for the supported Android app and invoked through a fixed trusted boundary.
- Define a typed render request derived from the validated timeline; never accept planner-supplied commands or shell fragments.
- Resolve every input by immutable artifact identity/hash and current workflow revision before renderer launch.
- Enforce explicit output path, dimensions, frame rate, duration tolerance, byte/storage limits, active runtime budget, and cancellation.
- Persist render attempt/result provenance and add the output through TASK-018/TASK-025 artifact contracts only after bounded process completion.
- Treat process crash, timeout, cancellation, resource exhaustion, malformed output, or missing output as explicit stage failure.
- Do not implement video inspection, preview/export UI, cloud media generation, publication, or generic command execution.

### Dependencies

- TASK-027 complete: deterministic media timeline representation.
- TASK-025 complete: media artifact schemas.
- TASK-018, TASK-020, TASK-023, and TASK-024 complete: immutable artifacts, revision invalidation, aggregate budgets, and Phase-3 durability acceptance.

### Plan

- Record an evidence-based renderer/toolchain decision covering Android packaging, ABI/API support, licensing, deterministic invocation, cancellation, and output support.
- Reuse the existing constrained process/cancellation boundary or introduce only the minimum renderer-specific adapter required.
- Translate validated timeline records into fixed arguments/config without shell interpolation.
- Stage output atomically, enforce resource budgets, and attach exact input/timeline/toolchain provenance.
- Add fake-adapter contract tests plus one real offline render path using bounded licensed fixture inputs.

### Acceptance

- A validated current-revision timeline produces a real video file at a deterministic artifact path.
- Renderer selection has recorded Android packaging/licensing/API evidence and no generic shell or arbitrary command surface.
- Every render binds exact timeline revision, input artifact hashes, renderer identity/version, output constraints, and final content hash.
- Unknown codecs/transitions, stale or missing inputs, invalid paths, insufficient storage, timeout, cancellation, crash, nonzero exit, or missing/oversized output fail closed.
- Partial output cannot be promoted to a verified media artifact or unlock downstream workflow nodes.
- Duplicate resume reuses a verified identical result or restarts only under durable current-revision state; it never silently duplicates uncertain work.
- Existing Stop/cancellation and aggregate budgets remain authoritative.

### Verification

- Renderer adapter contract tests with fixed argv/config and hostile-input/path negatives.
- Cancellation, timeout, crash, disk/resource-limit, stale-revision, partial-output, and duplicate-resume tests.
- Determinism/provenance/hash assertions across repeated identical fixtures.
- One real Android-compatible offline fixture render in CI or a clearly separated supported emulator/device evidence path.
- Canonical portable verification, Android build/lint/tests, license/architecture/security review.

### Expected result

Phase 4 gains a real bounded renderer that converts the deterministic timeline into an immutable video artifact without exposing arbitrary execution or treating an uninspected file as verified output.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R4.4 Renderer immediately after R4.3 timeline representation.
- Current TaskPlanner ends Phase-4 planning at TASK-027/R4.3; no existing task, open issue, or open PR represents R4.4.

### Projection basis

- R4.5 video inspection and R4.7 offline golden fixture require a real renderer output, while selecting the toolchain before timeline/schema contracts would create avoidable coupling.

### Risks / unknowns

- The exact toolchain and supported codec/container set remain an evidence-backed implementation decision constrained by Android packaging and licensing.
- Emulator rendering may not represent physical-device performance; evidence must remain labeled by environment.
- Renderer binaries can materially affect APK size and ABI support; keep the integration replaceable and bounded without creating a generic process framework.

---

## TASK-027: Define deterministic media timeline representation
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-4, media, timeline
**Updated:** 2026-10-03

### Goal

Define a strict deterministic timeline model that binds scenes, image/audio artifacts, captions, transitions, and output constraints into one renderer-ready revision without embedding rendering authority or provider behavior.

### Scope

- Define ordered scene records with stable IDs and explicit start/duration semantics.
- Reference immutable image and narration/audio artifacts from TASK-025/TASK-026 rather than copying media payloads into timeline state.
- Represent captions/subtitles with bounded text and timing.
- Represent bounded transition type/duration and output constraints such as target dimensions, frame rate, duration, and audio expectations.
- Bind timeline identity to workflow revision and exact referenced artifact hashes.
- Reject overlaps/gaps/invalid timing combinations according to a documented deterministic contract.
- Do not implement rendering, codec invocation, preview UI, external providers, or publication.

### Dependencies

- TASK-025 complete: media artifact schemas.
- TASK-026 complete: bounded narration pipeline.
- TASK-018 immutable artifact workspace and TASK-020 revision semantics.

### Plan

- Define minimal closed timeline/scene/caption/transition models.
- Validate referenced artifact type/hash/revision compatibility.
- Compute deterministic total duration and normalized scene ordering.
- Enforce bounded dimensions/frame rate/transition/caption timing and exact output constraints.
- Add serialization/round-trip, invalid-reference, timing, revision, and determinism tests.

### Acceptance

- Equivalent inputs serialize to one deterministic timeline representation.
- Every scene references exact immutable artifact identities and current workflow revision.
- Caption and transition timing cannot exceed scene/timeline bounds.
- Missing, stale-revision, wrong-media-type, duplicate-scene, invalid-duration, or inconsistent output constraints fail closed.
- Total timeline duration is deterministic and derived from validated scene timing.
- Timeline data cannot grant capabilities, approve effects, invoke renderers, or bypass verification.
- Revision of any referenced upstream artifact requires a new timeline revision rather than silent in-place mutation.

### Verification

- Focused timeline validation/round-trip/determinism tests.
- Scene ordering, overlap/gap, caption, transition, and total-duration tests.
- Wrong-type/hash/revision artifact-reference negatives.
- Output-bound and malformed-metadata tests.
- Canonical portable verification plus fresh architecture review.

### Expected result

Phase 4 has a stable renderer-neutral timeline contract connecting verified media artifacts into a deterministic 30–60 second video plan without coupling representation to execution.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R4.3 Timeline representation immediately after R4.2 narration.
- Current TaskPlanner represents R4.1 and R4.2 as TASK-025 and TASK-026; no current task, issue, or open PR represents R4.3.

### Projection basis

- Renderer and inspection layers need one deterministic source of scene timing and exact artifact references before a rendering toolchain can be selected safely.

### Risks / unknowns

- Exact transition catalog and frame-rate choices should remain minimal until renderer support is proven.
- Advanced editing, keyframes, effects, and nonlinear tracks are outside 1.0 scope.

---

## TASK-026: Implement bounded narration pipeline
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-4, media, narration
**Updated:** 2026-10-03

### Goal

Turn bounded script segments into verified narration audio artifacts with explicit duration/provenance while preserving speech-provider failure as a recoverable stage failure rather than task or workflow authority.

### Scope

- Accept ordered bounded script segments and synthesize narration through the provider-neutral speech interface.
- Persist each produced audio file through the immutable artifact workspace using TASK-025 media artifact schemas.
- Record segment order, source text hash/reference, provider identity/provenance, audio MIME/codec, byte size, duration, artifact hash, and workflow revision.
- Enforce bounded segment/input/output sizes, cancellation, timeout, and total narration duration.
- Validate produced audio duration/metadata before declaring the narration stage successful.
- Preserve deterministic typed/script artifacts if synthesis is unavailable or fails.
- Do not implement timeline composition, video rendering, playback UI, voice cloning, provider-specific SDK logic, or external publication.

### Dependencies

- TASK-009 complete: provider-neutral speech synthesis contract.
- TASK-018 complete: immutable artifact workspace.
- TASK-024 complete: Phase-3 durable-workflow acceptance gate.
- TASK-025 complete: media artifact schemas.

### Plan

- Define the smallest narration-segment request/result contract over existing speech synthesis and artifact APIs.
- Synthesize segments in deterministic order under explicit byte/time/call bounds.
- Store verified audio as immutable artifacts with source-segment and workflow provenance.
- Validate duration/media metadata and reject corrupt, oversized, mismatched, or empty outputs.
- Add cancellation/provider-failure/restart tests proving partial artifacts cannot masquerade as a completed narration stage.

### Acceptance

- Ordered script segments produce ordered immutable audio artifact references.
- Every narration artifact is bound to exact source segment/revision/provider provenance and verified content hash.
- Empty, malformed, oversized, wrong-media, or invalid-duration audio fails explicitly.
- Cancellation/timeout/provider failure cannot produce a successful narration-stage result.
- Restart cannot duplicate already-verified segment artifacts or silently skip incomplete segments.
- Narration failure does not equal workflow success/failure outside the declared stage transition and does not grant execution authority.
- Raw provider credentials never enter script, narration metadata, artifacts, logs, or durable workflow state.

### Verification

- Focused segment-order/synthesis/artifact round-trip tests.
- Duration/media/hash validation tests.
- Cancellation, timeout, provider-unavailable, malformed/oversized-output negatives.
- Restart/idempotency tests for partial and verified segment sets.
- Secret/provenance inspection.
- Canonical portable verification plus fresh architecture review.

### Expected result

LAIN_OS can produce durable, bounded, verified narration audio from script segments as real workflow artifacts that later timeline/render stages can consume without provider-specific or authority coupling.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R4.2 Narration pipeline immediately after media artifact schemas: script segments, synthesis, bounded audio file output, and duration validation.
- Current TaskPlanner represents R4.1 as TASK-025; no current task, issue, or open PR represents R4.2.

### Projection basis

- R4.3 timeline composition requires stable narration artifact references and durations; implementing narration first removes ambiguity from scene timing and renderer inputs.

### Risks / unknowns

- Exact audio codec/container set should stay limited to formats supported by TASK-025 and later renderer evidence.
- Streaming synthesis and advanced prosody are out of scope until a real provider/use case requires them.
- Hardware playback latency is unrelated to offline media narration generation and must not broaden this task.

---

## TASK-025: Define media artifact schemas
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-4, media, artifacts
**Updated:** 2026-10-03

### Goal

Define strict durable image/audio/video artifact metadata contracts that Phase 4 media stages can exchange without guessing MIME, codec, dimensions, duration, hash, or provenance.

### Scope

- Define bounded schema records for image, audio, and video artifacts.
- Include immutable content hash, media type/MIME, codec/container identifiers where applicable, dimensions, duration, byte size, provenance, producer node, workflow revision, and verification state.
- Reuse TASK-018 immutable artifact identities and TASK-020 revision semantics.
- Fail closed on impossible/contradictory metadata, hash mismatch, invalid dimensions/duration, or unsupported type combinations.
- Keep metadata non-authoritative: it cannot grant capabilities, approvals, execution, or publication rights.
- Do not implement synthesis, timelines, rendering, inspection tooling, preview UI, or provider adapters.

### Dependencies

- TASK-024 complete: Phase-3 durable-workflow acceptance gate.
- TASK-018 artifact workspace contracts remain authoritative.

### Plan

- Inventory existing artifact metadata and hashing primitives.
- Define minimal closed image/audio/video metadata variants with shared immutable identity/provenance fields.
- Add strict validation for MIME/codec/container/dimensions/duration/size combinations.
- Add serialization/round-trip and corrupt/inconsistent metadata tests.
- Document the contract consumed by later narration, timeline, renderer, and inspector tasks.

### Acceptance

- Image artifacts require valid dimensions and image media identity.
- Audio artifacts require valid duration and audio media identity.
- Video artifacts require valid dimensions, duration, and video media identity.
- Every artifact references immutable verified content identity and workflow revision/provenance.
- Invalid negative/zero dimensions, non-finite duration, impossible MIME/type pairings, oversized metadata, or hash mismatch fail explicitly.
- Metadata cannot authorize capabilities, approval, publication, or execution.
- Existing generic artifact workspace behavior remains reusable rather than duplicated.

### Verification

- Focused schema validation and round-trip tests.
- Cross-type invalid-combination tests.
- Hash/provenance/revision integrity tests.
- Metadata size-bound/corruption tests.
- Canonical portable verification plus fresh architecture review.

### Expected result

Phase 4 gains one stable media-artifact contract that narration, timeline, rendering, inspection, preview, and export can share without parallel type systems.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R4.1 Media artifact schemas as the first Phase-4 work package.
- Current planning reaches the Phase-3 acceptance gate at TASK-024; no open task, issue, or PR represents R4.1.

### Projection basis

- Every later Phase-4 stage exchanges real media files; stabilizing media identity and metadata first prevents renderer/inspector/UI-specific schemas from diverging.

### Risks / unknowns

- Final supported codec/container list should remain minimal until the chosen Android-compatible rendering path is proven.
- Rich metadata extraction belongs to video inspection, not this schema task.

---

## TASK-024: Close Phase-3 durable-workflow acceptance gate
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-3, acceptance, adversarial
**Updated:** 2026-10-03

### Goal

Prove the integrated durable-workflow subsystem survives process death, resumes truthfully, prevents replay of completed or uncertain effects, invalidates stale downstream artifacts after revision, and exposes an accurate user-readable workflow state before Phase 4 media work begins.

### Scope

- Exercise the integrated TASK-016 through TASK-023 workflow stack end to end.
- Verify crash/restart at scheduler, wait/poll, artifact, revision, and external-effect boundaries.
- Verify completed external effects cannot replay and uncertain effects cannot auto-retry.
- Verify upstream revision invalidates only transitive dependents while preserving immutable prior artifacts/provenance.
- Verify aggregate budgets persist and continue constraining resumed workflows.
- Verify restricted roles cannot expand capability authority.
- Verify user-readable workflow state distinguishes ready/running/waiting/reconciliation/succeeded/failed/cancelled truthfully.
- Do not add new workflow features, media rendering, provider-specific adapters, or publication behavior.

### Dependencies

- TASK-016 through TASK-023 complete.

### Plan

- Build the smallest deterministic acceptance harness over the integrated durable workflow APIs.
- Add process-restart fixtures around each critical durable transition.
- Exercise stale revision/hash, duplicate completion, uncertain effect, lease/wait, and budget exhaustion paths.
- Add user-readable state assertions derived from durable state rather than planner narration.
- Run canonical verification plus focused architecture/security review of the integrated Phase-3 boundary.

### Acceptance

- A multi-stage workflow resumes after simulated process death with exact durable state.
- Known completed effects cannot replay after restart.
- Attempted-but-uncertain effects enter reconciliation and never auto-retry.
- Revision invalidation rebuilds only dependent branches and preserves prior immutable artifacts.
- Wait/poll deadlines, scheduler leases, retries, and aggregate budgets survive restart truthfully.
- Restricted roles and workflow metadata cannot grant capability/policy/approval authority.
- Downstream nodes unlock only from verified/reconciled current-revision outputs.
- User-readable state matches durable workflow state without fabricated progress or completion.

### Verification

- End-to-end deterministic durable-workflow acceptance suite.
- Crash-boundary/restart matrix.
- Replay/uncertainty/reconciliation negatives.
- Revision/artifact invalidation and provenance checks.
- Budget/lease/wait/retry persistence checks.
- Canonical portable verification and fresh whole-diff architecture/security review.

### Expected result

Phase 3 has a reproducible gate proving durable workflows can survive interruption and revision without replay, stale authority, hidden budget reset, or false state before Phase 4 begins.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines an explicit Phase-3 exit gate after R3.1–R3.8.
- Current TaskPlanner represents R3.1–R3.8 as TASK-016 through TASK-023, but no existing task/issue/PR represents the exit-gate acceptance proof.

### Projection basis

- Phase 4 media pipelines create longer-running artifact-heavy workflows; carrying unresolved durability/replay defects into that layer would multiply integration cost and safety risk.

### Risks / unknowns

- Some external-provider reconciliation cases may require adapter-specific fixtures later; the core acceptance gate should use deterministic fakes and label anything not exercised against a live provider.
- Physical-device/UI acceptance remains separate unless explicitly exercised.

---

## TASK-023: Implement aggregate workflow budgets
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-3, workflow, budgets
**Updated:** 2026-10-03

### Goal

Enforce durable workflow-wide budgets for time, actions, provider calls, bytes, estimated/actual cost, and retries so long-running workflows cannot silently exceed owner-defined limits.

### Scope

- Persist workflow-level budget ceilings and consumed counters for time, action count, provider calls, bytes, estimated/actual cost, and retry allowance.
- Charge budget consumption at deterministic boundaries and persist it atomically with workflow state.
- Refuse new node execution, polling, provider work, or retry when the relevant remaining budget is insufficient.
- Preserve existing per-session/action budgets as lower-level limits; aggregate budgets may only further restrict execution.
- Carry budget state across restart, revision, wait/poll, and reconciliation states.
- Surface explicit budget-exhausted outcomes without treating them as successful completion.
- Do not implement billing APIs, dynamic price discovery, provider-specific token accounting, or automatic owner limit increases.

### Dependencies

- TASK-016 workflow persistence.
- TASK-017 DAG scheduler.
- TASK-021 durable wait/poll stages.
- TASK-022 external-effect reconciliation.

### Plan

- Define the smallest aggregate budget record and deterministic charging events.
- Persist counters/limits with workflow state and validate non-negative monotonic consumption.
- Gate scheduler dispatch, polling, provider calls, and retry before crossing each charge boundary.
- Preserve consumed state across crash/restart and workflow revision.
- Add fake-clock/counter tests for each budget dimension and combined exhaustion.

### Acceptance

- Workflow budgets survive restart exactly and consumed counters never decrease.
- Scheduler cannot dispatch work that would exceed a hard action/provider/retry limit.
- Time/deadline accounting cannot be reset by process restart or wait/poll transitions.
- Byte and cost accounting reject further bounded work once the configured ceiling is exhausted.
- Aggregate limits only reduce authority; they cannot expand lower-level runtime/session limits.
- Budget exhaustion produces an explicit non-success/waiting-for-owner outcome and cannot unlock downstream nodes.
- Revision and reconciliation preserve already-consumed budget unless an explicit future owner-authorized policy says otherwise.

### Verification

- Focused persisted-budget and monotonic-counter tests.
- Deterministic clock tests across wait/restart.
- Scheduler/provider/poll/retry gate tests for each budget dimension.
- Combined-limit and lower-level-budget-intersection negative tests.
- Canonical portable verification plus fresh architecture/security review.

### Expected result

LAIN_OS can run durable multi-stage workflows under explicit owner-visible aggregate resource limits without resets, hidden overages, or privilege expansion.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R3.8 Aggregate budgets after external-effect reconciliation.
- Current TaskPlanner state represents R3.1–R3.7 as TASK-016 through TASK-022; no open task, issue, or PR represents R3.8.

### Projection basis

- Media rendering, provider adapters, publishing, and long-running workflows require durable resource ceilings before broader 1.0 production pipelines can be considered safe and operable.

### Risks / unknowns

- Exact provider cost estimation may initially be caller-supplied or unavailable; unavailable estimates must not be fabricated.
- Provider-specific token accounting belongs in adapters, not the generic budget model.

---

## TASK-022: Implement external-effect reconciliation
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-3, workflow, reconciliation
**Updated:** 2026-10-03

### Goal

Make consequential external effects crash-safe by persisting exact operation identity before the side-effect boundary and requiring explicit reconciliation when the final outcome is uncertain.

### Scope

- Persist stable operation identity, workflow revision, node ID, effect type, payload hash, attempt state, and provider/external reference before crossing the effect boundary.
- Distinguish not-started, attempted/uncertain, confirmed-complete, failed-safe, and reconciliation-required states.
- Prevent automatic retry of uncertain effects after crash/restart.
- Prevent replay of effects already confirmed complete.
- Allow reconciliation to inspect external/provider state and settle the durable record without granting new authority.
- Preserve approval binding to exact workflow revision and payload hash.
- Do not implement provider-specific reconciliation adapters, publication, aggregate budgets, or multi-user conflict handling.

### Dependencies

- TASK-016 workflow persistence.
- TASK-017 DAG scheduler.
- TASK-020 revision invalidation.
- TASK-021 durable wait/poll stages.

### Plan

- Define the minimal durable external-operation record and state machine.
- Persist operation identity before invoking any consequential external write.
- Route crash/restart with attempted-but-unsettled state into reconciliation rather than retry.
- Add explicit settle transitions for externally confirmed success/failure.
- Reject stale revision/hash approvals and duplicate confirmed effects.
- Add deterministic crash-boundary and replay-prevention tests.

### Acceptance

- Operation identity is durably written before any external side effect is attempted.
- A crash after attempt but before confirmed receipt resumes in reconciliation-required state.
- An uncertain effect is never automatically retried.
- A confirmed completed effect cannot execute again after restart.
- Reconciliation cannot alter the approved payload, workflow revision, or capability authority.
- Stale approval/revision/hash combinations fail closed.
- Downstream workflow nodes unlock only after a reconciled/verified terminal result.

### Verification

- Deterministic crash-before/after-effect-boundary tests.
- Restart/replay-prevention tests.
- Duplicate operation identity and stale-revision/hash negative tests.
- Reconciliation settle tests with fake external state.
- Canonical portable verification plus fresh architecture/security review.

### Expected result

LAIN_OS can cross consequential external side-effect boundaries without replaying completed writes or guessing whether uncertain writes should be retried after process death.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R3.7 External-effect reconciliation immediately after durable wait/poll stages.
- Current TaskPlanner state represents R3.1–R3.6 as TASK-016 through TASK-021; no open task, issue, or PR represents R3.7.

### Projection basis

- Publishing, uploads, and external provider operations later in the 1.0 path require exact-once-oriented reconciliation semantics before those capabilities are introduced.

### Risks / unknowns

- Some providers lack idempotency or lookup APIs; such adapters may remain owner-reconciliation-only rather than pretending certainty.
- Provider-specific identifiers and status schemas must remain outside the generic reconciliation state machine.

---

## TASK-021: Implement durable wait and poll stages
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-3, workflow, waiting
**Updated:** 2026-10-03

### Goal

Add durable bounded waiting semantics for long provider, render, and upload stages without holding a worker indefinitely or silently extending controller budgets.

### Scope

- Persist explicit waiting state, wake/deadline metadata, provider/job identity references, poll attempt counts, and last observed provider state.
- Release active worker ownership while a node is waiting.
- Resume only when the persisted wake condition is reached or an external completion signal is reconciled.
- Bound poll intervals, total attempts, and deadline behavior under existing aggregate/runtime constraints.
- Preserve exact workflow revision and operation identity across process restart.
- Keep waiting metadata non-authoritative: it cannot grant capabilities, approve effects, or bypass verification.
- Do not implement provider-specific polling adapters, external-effect reconciliation, aggregate budget accounting, or publication behavior.

### Dependencies

- TASK-016 workflow persistence.
- TASK-017 bounded DAG scheduler.
- TASK-020 workflow revision invalidation.

### Plan

- Define a minimal durable waiting/poll state transition for workflow nodes.
- Persist wake deadline, attempt count, provider/job reference, and last safe observation atomically.
- Release scheduler lease when entering waiting and reacquire only when the node is eligible to poll.
- Enforce bounded backoff/poll count/deadline without consuming unbounded active controller time.
- Add restart, deadline, duplicate-poll, stale-revision, and cancellation tests.

### Acceptance

- Long-running nodes can enter a durable waiting state without retaining an active worker lease.
- Process restart preserves wait deadline, poll count, provider/job reference, and workflow revision exactly.
- Polling cannot occur before the persisted wake condition or after terminal deadline/cancellation.
- Poll attempts are bounded and cannot silently extend the node/controller budget.
- A stale workflow revision cannot resume or poll a superseded operation.
- Waiting state cannot authorize capabilities, approvals, or external effects.
- Completion observations remain subject to normal verification/reconciliation before downstream nodes unlock.

### Verification

- Focused wait-state transition and restart round-trip tests.
- Deadline/backoff/poll-limit tests with deterministic clocks.
- Lease-release/reacquisition tests against the scheduler.
- Negative stale-revision, cancellation, and duplicate-poll tests.
- Canonical portable verification and fresh architecture review.

### Expected result

LAIN_OS can pause durable workflow nodes for long external or rendering jobs and resume them truthfully after restart without blocking workers, replaying polls, or inventing extra runtime budget.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R3.6 Durable wait/poll stages directly after revision invalidation.
- Current TaskPlanner state represents R3.1–R3.5 as TASK-016 through TASK-020; no open task, issue, or PR represents R3.6.

### Projection basis

- Later media rendering, provider jobs, upload processing, and external reconciliation require persistent wait semantics that do not tie up execution workers or rely on in-memory timers.

### Risks / unknowns

- Provider-specific status schemas remain adapter concerns and must not leak into the core waiting model.
- External side-effect uncertainty belongs to TASK-022/R3.7 rather than being folded into polling.

---

## TASK-020: Implement workflow revision invalidation
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-3, workflow, revisions
**Updated:** 2026-10-03

### Goal
Add explicit workflow revisions and dependency-driven downstream invalidation so changing an approved upstream artifact creates a new revision without mutating or silently reusing stale dependent outputs.

### Scope
- Create a new workflow revision for accepted upstream changes.
- Compute the transitive set of dependent nodes/artifacts invalidated by that change.
- Preserve prior immutable artifacts and their provenance for audit/readback.
- Mark invalidated downstream work non-runnable until rebuilt from the current revision.
- Bind approvals and publication payloads to an exact workflow revision and artifact hashes.
- Reuse TASK-016 durable state, TASK-017 DAG dependencies, TASK-018 artifact identities, and TASK-019 restricted role metadata.
- Do not implement provider polling, external-effect reconciliation, publication, or generalized merge/conflict editing.

### Dependencies
- TASK-016 workflow persistence.
- TASK-017 DAG scheduler.
- TASK-018 artifact workspace.
- TASK-019 restricted specialist roles.

### Plan
- Define minimal revision and invalidation transitions over the persisted workflow graph.
- Derive transitive invalidation from declared dependency edges and artifact references.
- Preserve immutable prior artifacts while moving current logical references to new revision outputs.
- Reject stale approvals, node completions, and artifact references from older revisions.
- Add deterministic revision/invalidation/rebuild tests.

### Acceptance
- Revising one upstream artifact produces a new stable workflow revision.
- Every transitive dependent output is invalidated; unrelated branches remain valid.
- Invalidated nodes cannot run or report success from stale artifacts.
- Prior artifacts remain inspectable and immutable.
- Approval or publication records bound to an older revision/hash cannot authorize the new payload.
- Process restart preserves revision and invalidation state exactly.
- Revision metadata cannot grant capabilities or bypass policy, approval, execution, or verification.

### Verification
- Focused revision-transition and transitive-invalidation tests.
- Branch-isolation tests proving unrelated nodes stay valid.
- Restart/round-trip tests for invalidation state.
- Negative stale-approval, stale-artifact, and stale-completion tests.
- Canonical portable verification plus fresh architecture/security review.

### Expected result
A user revision such as “make it shorter” safely creates a new workflow revision and forces only dependent artifacts to rebuild, without mutating history or reusing stale authority.

### Evidence basis
- `docs/ROADMAP_1.0.md` defines R3.5 Revision invalidation immediately after R3.4 restricted specialist roles.
- Current TaskPlanner state covers R3.1 through R3.4 in TASK-016 through TASK-019; no open issue, PR, or task represents R3.5.

### Projection basis
- Voice-driven revisions, narration/render regeneration, and exact publication approval require deterministic stale-output invalidation before durable waits or external side effects are added.

### Risks / unknowns
- Concurrent edits and multi-user merge semantics remain out of scope for the single-active-workflow 1.0 path.
- Invalidation must stay graph-derived and minimal; broad “rebuild everything” behavior would hide dependency mistakes.

---

## TASK-019: Implement restricted specialist roles
**Priority:** P2 | **Tags:** overseer-assigned, developer, phase-3, workflow, roles
**Updated:** 2026-10-03

### Goal
Add bounded logical specialist roles for durable workflows while keeping all execution authority in the existing trusted runtime.

### Scope
- Define coordinator, writer, visual planner, narrator, renderer, and publisher roles.
- Restrict each role's visible context and capability families.
- Bind roles to durable workflow nodes and scheduler dispatch.
- Role restrictions may narrow existing authority only; they never grant policy, approval, execution, or verification authority.
- Reuse artifact references/provenance rather than exposing unrestricted workspace state.
- Do not add privileged independent executors or background daemons.

### Dependencies
- TASK-016 workflow persistence.
- TASK-017 DAG scheduler.
- TASK-018 artifact workspace.

### Plan
- Define a closed role catalog.
- Filter context and capability families at workflow-node dispatch.
- Intersect role allowances with existing registry/policy authority.
- Persist selected role and allowed families with workflow state.
- Add isolation and privilege-escalation tests.

### Acceptance
- Every specialist node uses one known restricted role.
- Role selection can only reduce available capabilities.
- Unrelated context, secrets, and artifacts remain unavailable.
- Unknown roles fail closed.
- Roles cannot approve work, alter policy, bypass verification, or select privileged executors.
- No parallel permission system is introduced.

### Verification
- Role catalog and context-filter tests.
- Capability-intersection tests.
- Cross-role isolation tests.
- Negative privilege-escalation tests.
- Canonical verification and architecture/security review.

### Expected result
LAIN_OS can dispatch bounded specialist perspectives inside a durable workflow while preserving one trusted authority layer.

### Evidence basis
- `docs/ROADMAP_1.0.md` defines R3.4 Restricted specialist roles after R3.1-R3.3.
- No current TaskPlanner task, open issue, or open PR represents R3.4.

### Projection basis
- Later revision, waiting, and media-production stages need explicit bounded stage roles without privileged autonomous sub-agents.

### Risks / unknowns
- Role-specific model/prompt choices remain deferred until actual stages require them.
- Capability-family granularity must reuse existing registry semantics.

---

## TASK-018: Implement immutable artifact workspace
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-3, workflow, artifacts
**Updated:** 2026-10-03

### Goal

Add the durable artifact workspace required for multi-stage workflows, using immutable content identity and explicit revision/provenance metadata without turning artifacts into executable authority.

### Scope

- Store workflow artifacts under immutable content hashes.
- Track logical artifact references, revisions, media/type metadata, provenance, producer node, and verification status.
- Use atomic writes and fail closed on hash mismatch or corrupt metadata.
- Expose user-visible workspace listing/readback without arbitrary path traversal.
- Define bounded retention/cleanup semantics that never delete artifacts still referenced by active/recoverable workflows.
- Keep artifact content/data non-authoritative: it cannot grant capabilities, approvals, or execution rights.
- Do not implement specialist roles, revision invalidation propagation, provider polling, or publication.

### Dependencies

- TASK-016 complete: durable workflow persistence model.
- TASK-017 complete: scheduler consumes artifact readiness.
- Existing safe filesystem/atomic-write/hash patterns should be reused.

### Plan

- Define artifact identity and metadata records around SHA-256 content hashes.
- Implement scoped atomic write/read/list APIs under a dedicated workspace root.
- Persist logical revision/provenance references in workflow-compatible metadata.
- Add reference-aware retention guards and explicit cleanup candidates.
- Add corruption/hash-mismatch/path-traversal and active-reference negative tests.
- Integrate only the minimal scheduler-facing readiness seam.

### Acceptance

- Artifact identity is immutable and derived from verified content bytes.
- Revisions create new identities rather than mutating prior content in place.
- Metadata preserves producer/provenance/type/revision/verification information.
- Hash mismatch or corrupt metadata fails explicitly.
- Artifact paths cannot escape the configured workspace root.
- Cleanup cannot remove artifacts still referenced by active or recoverable workflow state.
- Artifact content cannot authorize or execute capabilities.

### Verification

- Focused hash/round-trip/revision/provenance tests.
- Atomic-write and corruption/hash-mismatch tests.
- Path-traversal/symlink-escape tests.
- Retention tests with active/recoverable references.
- Canonical portable verification and architecture/security review.

### Expected result

LAIN_OS gains an inspectable, immutable artifact substrate for scripts, narration, media, and other workflow outputs without coupling content storage to execution authority.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R3.3 Artifact workspace after persistence and DAG scheduling.
- No current TaskPlanner task, open issue, or open PR represents R3.3.

### Projection basis

- Revision invalidation, specialist handoff, media production, and external publishing all require stable immutable artifact identities and provenance.

### Risks / unknowns

- Large media streaming/storage optimization should follow real workload evidence; v1 should prefer simple local bounded files.
- Retention policy must remain conservative until storage-pressure behavior is explicitly specified.

---

## TASK-017: Implement bounded DAG scheduler
**Priority:** P1 | **Tags:** overseer-assigned, developer, phase-3, workflow, scheduler
**Updated:** 2026-10-03

### Goal

Schedule ready workflow nodes from the durable TASK-016 model without allowing dependency violations, unbounded concurrency, or execution before required verified outputs exist.

### Scope

- Compute node readiness from explicit dependencies and durable node state.
- Support one active workflow initially.
- Use bounded worker leases with explicit acquisition/release/expiry semantics.
- Prevent downstream execution until required upstream outputs exist and satisfy their acceptance/verification predicates.
- Persist scheduler transitions through the workflow store before dispatching effects.
- Preserve trusted capability policy/approval/execution/verification/audit below the scheduler.
- Do not implement artifact storage, specialist role internals, revision invalidation, long polling, or external-effect reconciliation beyond the interfaces required to avoid unsafe replay.

### Dependencies

- TASK-016 complete: durable workflow persistence model.
- Existing trusted action runtime and verification semantics remain authoritative.

### Plan

- Define deterministic readiness rules over the persisted workflow graph.
- Detect dependency cycles and invalid/missing references before scheduling.
- Add bounded lease acquisition/renewal/release for ready nodes.
- Persist running/terminal scheduler transitions atomically around dispatch boundaries.
- Gate downstream readiness on verified required outputs, not planner claims.
- Add deterministic tests for ordering, cycles, lease contention/expiry, failure propagation, and verification-gated readiness.

### Acceptance

- A node becomes runnable only when all required dependencies satisfy their declared verified-output conditions.
- Cycles, missing dependencies, or invalid graph state fail closed.
- No two workers can hold the same active node lease simultaneously.
- Lease expiry cannot silently duplicate a known completed effect.
- Failed/cancelled/reconciliation upstream nodes do not incorrectly unlock dependents.
- Scheduler state cannot authorize capabilities or bypass policy/approval.
- One-active-workflow limit is enforced explicitly.

### Verification

- Focused DAG/readiness/cycle tests.
- Lease contention/expiry/recovery tests.
- Negative tests proving unverified upstream outputs cannot unlock downstream nodes.
- Crash-boundary tests around durable state transitions where deterministic.
- Canonical portable verification and fresh architecture review.

### Expected result

LAIN_OS can advance a durable workflow graph in dependency order with bounded ownership and verified-output gating while leaving effect authority in the existing trusted runtime.

### Evidence basis

- `docs/ROADMAP_1.0.md` defines R3.2 DAG scheduler immediately after the workflow persistence model.
- No current TaskPlanner task, open issue, or open PR represents R3.2.

### Projection basis

- Artifact, specialist, revision, wait/poll, and reconciliation layers all need deterministic dependency readiness and bounded node ownership.

### Risks / unknowns

- Cross-process/distributed leases are out of scope unless runtime topology actually requires them; start with the smallest local durable lease semantics.
- Exact reconciliation behavior for uncertain external effects belongs to R3.7 and must not be pre-implemented here.

---

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

