# LAIN_OS — Voice Agent Suite: 1.0 Design

Version: 1.0-draft · 2026-10-01

Status: product design specification. This document defines intended application behavior and acceptance targets; implementation and verification status are tracked separately.

## Product intent

LAIN_OS is the **Local Autonomous Intelligence Network Operating System**, the concrete software platform implementing the broader **LAIN — Loyal Autonomous Intelligence Network** identity.

LAIN_OS is a voice-first autonomous agent suite that converts natural conversation into complex, verified action sequences under the user's control. The user speaks normally, receives spoken responses while work progresses, and can interrupt, revise, pause, or stop a task. Specialist workers share one coherent conversational interface and operate through the trusted runtime.

Flagship scenario: “Turn this idea into a YouTube video and post it.” Success means a real rendered video, user review when required, authorized upload/publication, and an independently retrieved result. A generated script, mocked upload, or planner assertion is not completion.

Interpretation: “my voices” means the user's spoken input and selectable agent speech voices. Voice cloning, multiple simultaneous speakers, and multiple independently speaking agent personas are not assumed requirements. They can be added after clarification. Use licensed stock speech voices initially.

## Product baseline

LAIN_OS already provides the trusted execution foundation this design builds on:
typed action validation, capability policy, deterministic execution, verification,
audit, bounded autonomous sessions, Android integration, exact approvals, Stop
controls, and durable recovery semantics.

The 1.0 design extends that foundation with real selectable planners, voice
conversation, durable multi-stage workflows, media production, and narrowly scoped
publishing. Those additions must preserve the existing authority boundary rather
than replacing it with direct model-driven execution.

## Recommended architecture

Use a native Android conversational client embedding the existing Python control core, plus replaceable speech, reasoning, media, rendering, and publishing adapters. Execute supported local operations locally. Allow user-configured remote services for resource-intensive work, with explicit disclosure of data leaving the device and trusted spending limits.

Alternatives considered: an entirely local implementation improves offline operation but makes initial speech/media performance and phone resource use harder; a thin cloud client accelerates integrations but weakens local ownership and depends on a server. Recommend the hybrid approach, retaining local policy, durable state, and control. Provider and renderer selection remains an implementation research decision, not a dependency commitment.

Separate subsystems:

- Conversation: microphone input, speech recognition, turn handling, text transcript, selectable speech synthesis, playback cancellation, and concise progress narration.
- Orchestration: durable task graph, specialist roles, dependencies, bounded replanning, progress evidence, cancellation, and recovery.
- Trusted capabilities: typed local/device operations and narrowly scoped provider/render/upload operations behind policy.
- Artifact workspace: versioned scripts, narration, visual assets, captions, rendered files, manifests, and provenance.
- Publishing: user account authorization, private upload staging, processing checks, exact publication approval, and independent result lookup.

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

Keep read-only user inspection and emergency stop available even when a worker lease is held. Enforce one active workflow initially. Parallel specialist execution is optional later and requires compatible leases, fixed output ownership, and aggregate budgets.

## Flagship video workflow

V1 scope: a short narrated video assembled from user-provided or authorized generated images, captions, and simple transitions. Arbitrary cinematic video generation, avatars, and voice cloning are later extensions. Proposed offline fixture: a 30–60 second video using bundled licensed assets; it must exercise a real renderer and inspect the actual output.

Stages: capture idea → outline/script → narration → visual assets → render → inspect preview → upload privately → check processing → approve publication → publish → retrieve video metadata/link.

Proposed capability families, each requiring schema, risk, permissions, environment support, error codes, verification, cancellation, and duplicate handling before implementation:

| Family | Purpose | Required evidence |
|---|---|---|
| speech.transcribe / speech.synthesize | Convert user speech and render narration | Final transcript metadata; decodable audio and duration |
| media.generate_image | Produce bounded requested visuals | Downloaded, decodable asset; dimensions/hash and provenance |
| media.render_video / media.inspect_video | Assemble and inspect the video | Actual file, streams, duration, dimensions, audio, and file hash |
| youtube.upload / youtube.status | Upload to the user's channel and inspect processing | Persisted upload/video ID and independent authenticated lookup |
| youtube.publish | Apply approved public metadata/visibility | Retrieved visibility and metadata associated with the exact video ID |

These names are proposals, not existing registry entries. Text planning can remain a planner task; do not register generic “execute agent code” or arbitrary authenticated HTTP capabilities.

External generation may transmit private data and incur cost. Uploading privately is still an external write and needs account/data-transfer authority. Bind approvals to exact artifact hash, destination channel, title, description, visibility, policy revision, nonce, and expiry. Never treat “post it” in a design example as permission to publish a real test video now. Avoid claiming a published video is publicly accessible while processing or visibility verification is incomplete.

Use user-selected OAuth account authorization and minimum required scopes. Store tokens with Keystore-backed protection in the app. Scope, verification, quota, resumable-upload behavior, and platform metadata requirements must be checked against current official documentation during implementation. Never request passwords or copy tokens into build artifacts.

## Delivery graph and acceptance

The product dependency graph is ordered by the interfaces and trust boundaries each stage requires.

| ID | Dependencies | Deliverable and acceptance |
|---|---|---|
| F0 | none | Fresh baseline, repository instructions, tool capability inventory, actual portable verification results, and reconciled durable plan |
| F1 | F0 | Existing standalone APK milestone: embedded core, native adapters, GUI, exact approvals, stop/recovery; build and installed-demo evidence |
| F2 | F1 | Voice conversation: real microphone-to-transcript and synthesis-to-speaker; interruption, echo, permission-denied/offline/rotation tests; latency record |
| F3 | F1 | Durable workflow graph: dependencies, artifact hashes, bounded workers, revisions, cancellation, crash recovery, and uncertain-effect reconciliation tests |
| F4 | F2,F3 | Offline video fixture: actual narration/assets/rendered video, media inspection, preview/export; preserve mobile responsiveness and stop behavior |
| F5 | F3,F4 | Provider adapters: configured speech/media/planner integration, cancellable transport, budgets, throttling/error handling; fake transports first |
| F6 | F2,F5 | YouTube authorization, resumable upload, processing checks, exact publication gate, lookup; contract tests first, user-authorized private live test separately |
| F7 | F1–F6 | End-to-end spoken idea-to-video scenario, interruption/revision/recovery, final installed APK checks and release-readiness report |

A 1.0 claim requires the documented core scope to work through real installed artifacts, not just adapters mocked in tests. Missing device, build/signing infrastructure, live credentials, or required acceptance evidence remains explicit. Preserve CLI compatibility and existing tests. No public release claim for a debug APK. Keep persistent maintainer-controlled release signing and reviewed update/state migration behavior.

## Design summary

This design selects a hybrid architecture, one active workflow, user-started voice sessions, stock voices, and a deliberately narrow first video format for 1.0. The product remains local-authority-first even when remote reasoning, speech, media, or publishing services are configured.

