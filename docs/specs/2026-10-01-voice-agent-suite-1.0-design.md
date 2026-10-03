# LAIN_OS — Voice Agent Suite: 1.0 Design and GodPrompt Brief

Version: 1.0-draft · 2026-10-01 · ROLE=PLANNER

Status: product direction selected by the user; proposed architecture and implementation stages below are reviewable planning artifacts. No product code, build, hardware test, publication, or deployment was performed for this brief.

## Product intent

LAIN_OS is a voice-first autonomous agent suite that converts natural conversation into complex, verified action sequences under its owner's control. The owner speaks normally, receives spoken responses while work progresses, and can interrupt, revise, pause, or stop a task. Specialist workers share one coherent conversational interface and operate through the trusted runtime.

Flagship scenario: “Turn this idea into a YouTube video and post it.” Success means a real rendered video, owner review when required, authorized upload/publication, and an independently retrieved result. A generated script, mocked upload, or planner assertion is not completion.

Interpretation: “my voices” means the user's spoken input and selectable agent speech voices. Voice cloning, multiple simultaneous speakers, and multiple independently speaking agent personas are not assumed requirements. They can be added after clarification. Use licensed stock speech voices initially.

## Inspected baseline and limits

Sources: attached LAIN_OS-main.zip and LAIN_OS-next-phase-handoff.zip. The main archive identifies commit 24ec1621fd63aaa6ce74f34c322d7b371b823ff6; its README describes the Python runtime, typed action validation, policy, executor, verification, audit, planner adapters, and bounded durable autonomous sessions. No native Android GUI is present in that snapshot.

The handoff describes a newer inspected baseline, naminemirai/LAIN_OS_DEVBRANCH@19482fda2348e3aa0057c470b96cbc426e73bba9, with expanded Android capabilities and historical CI/hardware evidence. These snapshots differ. Inspect the actual repository at execution time; do not reset a newer branch or assume the older archive contains newer features. Historical test counts and hardware results are not fresh verification.

The existing standalone-workbench design and plan remain foundational. Preserve their private runtime service, authenticated same-UID Binder control, bounded execution, exact approvals, conservative recovery, scoped filesystem, native adapters, portable CLI, and APK acceptance requirements. This brief extends their product destination; it does not certify their implementation.

## Recommended architecture

Use a native Android conversational client embedding the existing Python control core, plus replaceable speech, reasoning, media, rendering, and publishing adapters. Execute supported local operations locally. Allow owner-configured remote services for resource-intensive work, with explicit disclosure of data leaving the device and trusted spending limits.

Alternatives considered: an entirely local implementation improves offline operation but makes initial speech/media performance and phone resource use harder; a thin cloud client accelerates integrations but weakens local ownership and depends on a server. Recommend the hybrid approach, retaining local policy, durable state, and control. Provider and renderer selection remains an implementation research decision, not a dependency commitment.

Separate subsystems:

- Conversation: microphone input, speech recognition, turn handling, text transcript, selectable speech synthesis, playback cancellation, and concise progress narration.
- Orchestration: durable task graph, specialist roles, dependencies, bounded replanning, progress evidence, cancellation, and recovery.
- Trusted capabilities: typed local/device operations and narrowly scoped provider/render/upload operations behind policy.
- Artifact workspace: versioned scripts, narration, visual assets, captions, rendered files, manifests, and provenance.
- Publishing: owner account authorization, private upload staging, processing checks, exact publication approval, and independent result lookup.

Agent roles are restricted logical workers, not privileged independent executors. A script writer, visual planner, editor, and publisher receive only the context and capabilities needed for their task. Model output cannot select arbitrary executors, import code, change policy, or authorize spending. Workers share durable artifacts and typed results rather than unlimited transcripts.

## Voice and interaction contract

Initial behavior: user-started voice sessions with a visible microphone state; text input always remains available. No always-listening microphone or wake-word requirement for the first release. Installation and the offline demonstration require no cloud account. Offline speech is advertised only if an available engine has actually been tested.

Allow speech input while synthesis is playing. On detected user speech, stop or duck playback and route the new utterance as a conversational turn. Acoustic echo must not become a self-generated command. Transcription is a proposal: ambiguous or low-confidence consequential instructions require clarification. Only final recognized turns may initiate ordinary tasks; partial transcripts cannot grant approval.

Maintain a distinct conversation stream and durable execution state. Speaking a response does not block the worker; losing speech transport does not imply task cancellation. “Stop talking” stops playback. “Stop the task” enters the trusted execution control path. An explicit on-screen Stop remains available during recognition or network failure.

Revision example: “Make it shorter” updates the draft and invalidates affected downstream artifacts. It does not mutate an already approved publication payload. If publishing is already in flight, report that fact and reconcile its outcome. Cancellation cannot promise rollback of an external effect.

Use monotonic turn IDs, session revisions, and an explicit active-task reference. Require clarification when an utterance could refer to several tasks. Store raw audio only by explicit opt-in; redact secrets from transcripts and logs. Obtain microphone permission through Android's normal UI and keep recording visible.

Acceptance targets: measured user-interruption-to-playback-stop at most 500 ms on the declared reference device; trusted pause/cancel receipt within two seconds in controlled tests. These are proposed measurable targets, not observed performance. Report recognition, reasoning, and first-audio latency separately; do not promise instantaneous cloud responses.

## Complex workflow contract

Introduce a durable task graph above the existing action-batch controller, not a replacement executor. Each task records ID, dependencies, status, input/output artifact references and hashes, assigned role, allowed capabilities, acceptance checks, attempted operations, consumed budgets, and error/recovery state.

Use pending, ready, running, waiting_for_owner, succeeded, failed, cancelled, and reconciliation states. Only verified required outputs satisfy downstream dependencies. Persist operation intent and identity before crossing a side-effect gate. Completed effects must not replay after process death. An uncertain upload or provider charge requires reconciliation, not blind retry.

Retain existing finite controller defaults within each bounded execution run. Long media jobs use explicit durable wait/poll stages and task-level limits; they do not silently increase the controller's runtime budget. Persist deadlines, retry counts, estimated/actual costs, provider job IDs, and output ownership. Provider estimates cannot grant spending authority.

Keep read-only owner inspection and emergency stop available even when a worker lease is held. Enforce one active workflow initially. Parallel specialist execution is optional later and requires compatible leases, fixed output ownership, and aggregate budgets.

## Flagship video workflow

V1 scope: a short narrated video assembled from owner-provided or authorized generated images, captions, and simple transitions. Arbitrary cinematic video generation, avatars, and voice cloning are later extensions. Proposed offline fixture: a 30–60 second video using bundled licensed assets; it must exercise a real renderer and inspect the actual output.

Stages: capture idea → outline/script → narration → visual assets → render → inspect preview → upload privately → check processing → approve publication → publish → retrieve video metadata/link.

Proposed capability families, each requiring schema, risk, permissions, environment support, error codes, verification, cancellation, and duplicate handling before implementation:

| Family | Purpose | Required evidence |
|---|---|---|
| speech.transcribe / speech.synthesize | Convert owner speech and render narration | Final transcript metadata; decodable audio and duration |
| media.generate_image | Produce bounded requested visuals | Downloaded, decodable asset; dimensions/hash and provenance |
| media.render_video / media.inspect_video | Assemble and inspect the video | Actual file, streams, duration, dimensions, audio, and file hash |
| youtube.upload / youtube.status | Upload to the owner's channel and inspect processing | Persisted upload/video ID and independent authenticated lookup |
| youtube.publish | Apply approved public metadata/visibility | Retrieved visibility and metadata associated with the exact video ID |

These names are proposals, not existing registry entries. Text planning can remain a planner task; do not register generic “execute agent code” or arbitrary authenticated HTTP capabilities.

External generation may transmit private data and incur cost. Uploading privately is still an external write and needs account/data-transfer authority. Bind approvals to exact artifact hash, destination channel, title, description, visibility, policy revision, nonce, and expiry. Never treat “post it” in a design example as permission to publish a real test video now. Avoid claiming a published video is publicly accessible while processing or visibility verification is incomplete.

Use owner-selected OAuth account authorization and minimum required scopes. Store tokens with Keystore-backed protection in the app. Scope, verification, quota, resumable-upload behavior, and platform metadata requirements must be checked against current official documentation during implementation. Never request passwords or copy tokens into build artifacts.

## Delivery graph and acceptance

All tasks are pending. Implement by dependency after the written design and plan reviews required by the applicable workflow.

| ID | Dependencies | Deliverable and acceptance |
|---|---|---|
| F0 | none | Fresh baseline, repository instructions, tool capability inventory, actual portable verification results, and reconciled durable plan |
| F1 | F0 | Existing standalone APK milestone: embedded core, native adapters, GUI, exact approvals, stop/recovery; build and installed-demo evidence |
| F2 | F1 | Voice conversation: real microphone-to-transcript and synthesis-to-speaker; interruption, echo, permission-denied/offline/rotation tests; latency record |
| F3 | F1 | Durable workflow graph: dependencies, artifact hashes, bounded workers, revisions, cancellation, crash recovery, and uncertain-effect reconciliation tests |
| F4 | F2,F3 | Offline video fixture: actual narration/assets/rendered video, media inspection, preview/export; preserve mobile responsiveness and stop behavior |
| F5 | F3,F4 | Provider adapters: configured speech/media/planner integration, cancellable transport, budgets, throttling/error handling; fake transports first |
| F6 | F2,F5 | YouTube authorization, resumable upload, processing checks, exact publication gate, lookup; contract tests first, owner-authorized private live test separately |
| F7 | F1–F6 | End-to-end spoken idea-to-video scenario, interruption/revision/recovery, final installed APK checks and release-readiness report |

A 1.0 claim requires the documented core scope to work through real installed artifacts, not just adapters mocked in tests. Missing device, build/signing infrastructure, live credentials, or required acceptance evidence remains explicit. Preserve CLI compatibility and existing tests. No public release claim for a debug APK. Keep persistent owner-controlled release signing and reviewed update/state migration behavior.

## GodPrompt execution brief

You are the LAIN_OS principal engineering agent. Begin in ROLE=PLANNER for the new voice/workflow/media design, then hand off to ROLE=DEVELOPER only after the applicable written spec and implementation-plan gates are complete. Use this document and the existing standalone Android handoff as inputs; conversation memory is not repository state.

Mission: deliver a standalone Android voice agent suite that can understand normal spoken goals, converse while working, execute bounded complex workflows through the existing trusted runtime, and demonstrate a real idea-to-video workflow with separately authorized publication.

1. Inspect actual source, instructions, branch/commit, dirty state, approvals, existing durable goals/plans, and available build/device/network tools. Reconcile the two supplied baseline snapshots. Preserve unrelated work and record facts separately from assumptions.
2. Produce the repository-native written design and task plan for F0–F7. Resolve provider/rendering/toolchain feasibility with current official documentation and bounded probes. Prefer one native conversational interface over specialist workers; retain typed policy-controlled actions. Do not silently replace the standalone app with a Termux/server client.
3. Implement authorized tasks in dependency order after required reviews. Establish meaningful behavior failures before fixes, run focused verification, then required broader checks. Preserve the portable CLI, safe recovery, exact approvals, budgets, and capability boundaries.
4. Implement real voice/media paths. Test doubles are appropriate for failure contracts but cannot certify hardware speech, actual rendering, uploads, or publication. Clearly label demo planners and offline fixtures.
5. Do not spend, create paid infrastructure, publish content, merge, deploy, or send messages without corresponding authority. Continue independent local implementation when credentials or infrastructure block a later stage. Do not invent a successful external operation or weaken verification to finish.
6. Verify interruption during synthesis and planning, revision during production, crash after an external effect, duplicate approval/upload, provider timeout/429, exhausted budget, microphone denial/revocation, corrupt state, hostile tool output, path escape, and secret leakage. Measure the stated control targets on declared environments.
7. Deliver source changes, exact commands/exit codes, test results, artifacts/hashes/signers, installed-device evidence, known limits, pending task IDs, and next action. Distinguish implemented, tested, built, installed, observed, release-signed, published, reviewed, and merged. Update durable task state after each completed unit.

Do not end with architecture alone once implementation is authorized. Do not claim 1.0 until its required acceptance evidence exists. If blocked, finish independent authorized work and leave a concrete recovery handoff rather than a vague promise.

## Review and next action

This brief selects a hybrid architecture, one active workflow, user-started voice sessions, stock voices, and a deliberately narrow first video format as proposed defaults. No implementation approval is inferred from those choices. Next: review this written design, then expand F0–F7 into repository-specific implementation steps and verify the current execution environment.

Planning check: baseline conflicts documented; voice and workflow semantics separated; external authority distinct; capability names labeled proposed; all tasks have dependencies and observable acceptance; no code/build/publication completion claims.
