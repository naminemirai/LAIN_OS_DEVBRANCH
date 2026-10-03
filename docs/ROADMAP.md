# LAIN_OS Roadmap

**Local Autonomous Intelligence Network Operating System**

## Current 1.0 implementation focus — 2026-10-03

TASK-008 Phase-1 planner acceptance is the active gate before voice work. PR #16 head `c700eed0b9de6964729a6b038eaa565daf44864d` is automated GREEN (Verify #270; Android #259), and the exact debug build has begun physical Galaxy acceptance.

Current device evidence is mixed by design: Offline Demo **Show battery** reaches **COMPLETE**, while the real selected Groq planner path reaches the provider but is rejected with HTTP 400 because LAIN generates an invalid strict JSON schema for a zero-argument capability. The current one-token structured-output connection probe also produces independent validation failures. These are active TASK-008 defects; they are not credential/network failures and must not be hidden behind `unavailable`.

Before TASK-008 closes, the patch must preserve the trust boundary, rerun full CI, produce a new exact-GREEN APK, prove Stop on a genuinely in-flight planner call, and require the complete applicable Workbench preset suite — Create demo file, Show battery, Show demo toast, Vibrate briefly, Copy demo text, Share demo text — to reach terminal **COMPLETE** through the real selected planner, with exact approval on sharing. See `docs/ROADMAP_1.0.md`, `docs/ANDROID_ACCEPTANCE.md`, `.tasks/NEXT.md`, and issue #6 for the canonical current gate.

## v0 — Local loop

Goal: prove the architecture with a small, inspectable control path.

Deliverables:
- action-envelope schema;
- capability registry;
- permission policy;
- local executor;
- result verification;
- append-only audit log;
- three safe capabilities:
  - create/move/copy a file;
  - post an Android notification;
  - launch a standards-based Android intent.

Exit condition:

A natural-language request can become a typed action, execute locally, verify success, and produce an audit record without unrestricted screen automation.

Status: runtime and planner boundary implemented and covered by portable tests.
Notification/URI/audit were manually validated on real F-Droid Termux + matching
Termux:API. A real configured Groq planner completed a live Android/Termux autonomous
session: two file actions (`hello.txt` = `hello`, `done.txt` = `finished`) executed
and independently verified PASSED, then Groq observed verified history and returned
complete. Manual hardware evidence is not automated Android CI; live interruption/
resume is a separate acceptance case.

## v0.0.1 — First external write

- expose only `reddit.create_post` as a Class 2 capability;
- require explicit confirmation;
- use locally supplied OAuth refresh-token credentials;
- prevent duplicate execution by `request_id` and never automatically retry ambiguous writes;
- verify returned post metadata with an independent lookup;
- keep credentials and submitted bodies out of audit records.

Live Reddit testing is opt-in and is not part of the unit suite.

## v0.1 — Workbench bridge

Add practical workflow actions:
- route shared text into an inbox;
- route PDFs/documents by type;
- create project folders from templates;
- archive a project;
- write Markdown capture files;
- invoke Git status/build/test commands through constrained wrappers.

## v0.2 — Android Capability Expansion v1

Implemented with portable tests and manual Android/Termux hardware acceptance
completed at exact feature head
`0d7efe584b78a050c2817b2ab3e3f555e2450dff`:
- read-only structured `android.battery_status`;
- bounded `android.vibrate` and short `android.toast`;
- write-only `android.clipboard_set`, with private immediate comparison;
- confirmed `android.share_text`, opening only a user-visible chooser;
- reusable private Termux command boundary with timeout/output limits and filtered
  environment; no generic command or device-control capability;
- honest PASSED/FAILED/LIMITED verification and recursive payload redaction.
- physical acceptance observed battery and clipboard PASSED, toast/vibration/share
  LIMITED as designed, the share confirmation barrier, and audit content redaction.

Next Android sub-milestone: individually reviewed narrow Shizuku-backed
capabilities where native intents and Termux:API cannot serve the operation.
Tasker bridges, receivers, notification listeners, file observers and widgets
remain later scope. AccessibilityService and visual/coordinate automation remain
explicit fallbacks, not the foundation. See [hardware acceptance](ANDROID_ACCEPTANCE.md).

## v0.3 — Local agent runtime

Implemented bounded foreground autonomy:
- provider-independent subprocess planner boundary;
- explicit planner lifecycle decisions: `continue | complete | blocked`;
- model-independent bounded action batches;
- durable resumable sessions with atomic per-action checkpoints;
- finite iteration/action/runtime budgets;
- interruption-safe resume without replay of completed actions;
- conservative audit-ahead-of-checkpoint reconciliation;
- explicit cancellation;
- human confirmation pause/resume gates;
- exclusive per-session execution leases.

The v0.3 implementation is deliberately on-demand/foreground. Persistent background services, scheduled wakeups, event triggers, and unrestricted AccessibilityService automation remain later milestones.

## v0.4 — Multi-node LAIN_OS

Add authenticated local networking:
- node identity;
- discovery;
- capability advertisement;
- encrypted transport;
- remote action approval;
- per-node audit logs.


## v1.0 — Secure Android APK ("do the thing" surface)

Package LAIN_OS as a production-oriented Android application that exposes the trusted runtime through a minimal, human-controlled command surface.

Primary user story:

```
"do the thing"
    ↓
intent capture
    ↓
planner
    ↓
typed action
    ↓
policy / confirmation
    ↓
trusted capability
    ↓
verification
    ↓
audit + result
```

The APK must preserve the existing trust model rather than collapsing planner, authorization, and execution into one privileged process.

Security requirements:
- Kotlin + AndroidX; Google Play Services must not be required;
- release builds signed with a user-controlled signing key;
- reproducible/CI-verifiable release build where practical;
- minimize exported activities, services, receivers, and providers;
- explicit component permissions and intent validation;
- scoped storage by default; avoid broad/all-files access unless a capability demonstrably requires it;
- Android Keystore-backed protection for locally stored secrets and tokens;
- no credentials, recovery material, or private payloads in logs;
- authenticated, narrowly scoped IPC between the Android UI/control plane and the LAIN_OS runtime;
- capability allow/deny controls visible to the user;
- device-credential or biometric confirmation option for high-risk external/destructive actions;
- emergency stop / disable-execution control;
- clear foreground/background execution state;
- signed update integrity and rollback-aware release process;
- dependency and manifest review as part of release verification;
- tests for exported-component abuse, malformed intents, replay/duplicate requests, path escapes, secret leakage, and authorization bypasses.

Initial app surfaces should remain intentionally small:
- command/intention entry;
- share-sheet target;
- confirmation sheet for consequential actions;
- recent action + verification/audit view;
- capability/settings screen;
- optional Quick Settings tile, widget, or notification action for fast invocation.

Do not implement unrestricted AccessibilityService automation as the foundation. Prefer typed Android APIs, intents, local adapters, and deterministic capabilities. Accessibility-based control remains an explicitly reviewed fallback.

Exit condition:

A signed APK can accept a user command, convert it into the existing ACTION_PROTOCOL flow, obtain required confirmation, execute an allowed local or authenticated capability, verify the result, and present the audit trail without granting the planner unrestricted device authority.

## Later

Possible research tracks:
- persistent background agent service and event-driven wakeups;
- local speech interface;
- on-device models;
- visual UI fallback;
- sensor fusion;
- repository-native coding agents;
- shared memory indexing;
- offline semantic search.

## Explicitly deferred

- cloud account dependency;
- unrestricted AccessibilityService autonomy;
- autonomous purchasing or money movement;
- secret storage design;
- internet-exposed remote control;
- self-modifying policy.
