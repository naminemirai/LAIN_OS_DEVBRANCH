# LAIN_OS Android Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a standalone Android GUI and debug APK exposing the existing trusted LAIN_OS runtime.

**Architecture:** Embed Python in a Kotlin application through Chaquopy. A non-exported service in the private `:runtime` process authenticates same-UID Binder calls and routes bounded typed control messages to a Python app controller. A single worker advances existing durable agent sessions; inspection and cooperative Stop use a separate control path.

**Tech Stack:** Kotlin, AndroidX, Android SDK, Gradle, Chaquopy, Python 3.11. Use conventional Android views for this first interface; no web server or WebView bridge. Pin compatible build versions after reading current toolchain documentation.

**Spec:** `docs/superpowers/specs/2026-10-01-android-interface-design.md`; product destination: `docs/superpowers/specs/2026-10-01-voice-agent-suite-1.0-design.md`.

> 2026-10-01 update: the owner resumed tests, CI, and device validation.
> The original pause instructions below are historical; follow the current
> evidence in docs/ANDROID_APP.md.

## Global Constraints

- Standalone APK; no Termux/server dependency. Preserve the portable CLI.
- Keep planner output untrusted; validation, policy, execution, verification, and audit stay authoritative.
- Same-UID Binder control, private runtime process, one active run, app-private storage.
- No generic shell, arbitrary intents, clipboard getter, or model-issued approvals.
- Command entry, progress/results, exact-action confirmation, session history, Stop.
- Verification runs are paused by the owner; do not claim tests, CI, or hardware acceptance.
- A debug APK build may produce the requested artifact; no public release, deployment, merge, or paid/provider operation.
- Native runtime changes require their own device acceptance; the earlier Termux acceptance does not certify them.

## Review Focus

- Rotation/rebinding during execution must recover durable state without submitting a duplicate task (Task 4).
- Foreign-UID, unknown command, oversized or malformed control input must fail closed (Tasks 1, 3).
- Stale or repeated approval must never authorize a different request/action (Task 1).
- Stop during an in-flight action must prevent subsequent actions and report the settled outcome honestly (Task 1).
- Clipboard/share content, credentials, and raw adapter errors must not appear in history, UI logs, or Binder diagnostics (Tasks 1, 2, 4).

## Baseline and execution notes

Inspected `main`: `7abec73ea4bd096b4b6c69cf66745bf6115412e1`. The 90-file source snapshot contains no Android application module and no `AGENTS.md`. Git clone is blocked by an unreachable inherited proxy; the source snapshot was retrieved through the authenticated GitHub connector and is not a Git checkout. Preserve that distinction. Use an isolated local source directory; recover a genuine checkout or publish new commits through GitHub Git-data operations only when publication is authorized. Do not fabricate baseline history.

Java 21 and Python are available. Gradle and `adb` were not found on PATH. APK assembly requires an Android SDK and downloadable pinned build dependencies. Continue source implementation if build setup is externally blocked; report an absent APK precisely. The older standalone-workbench handoff referenced in the voice brief is unavailable, so this plan preserves its requirements explicitly stated in that brief.

All verification steps below are deferred, not skipped acceptance. Author their test cases without running them during this pass.

### Task 1: Embedded application control boundary

**Files:**
- Create: `lain/app/__init__.py`, `lain/app/control.py`, `lain/app/demo.py`.
- Test: `tests/test_app_control.py`.

**Interfaces:**
- Consumes: `RuntimeConfig`, `RuntimeEngine`, `AgentController`, `AgentSessionStore`, `AgentPlanningService`, and existing recursive audit redaction.
- Produces: `AppController(root: Path, native: object | None = None)` with `dispatch(payload: str) -> str` for `start`, `inspect`, `sessions`, `approve`, and `stop`; `advance() -> bool` runs at most one bounded controller step. Java calls `create_controller(root: str, native: object) -> AppController`.
- Request schema: exact fields `version=1`, `command`, `arguments`; reject unknown fields, JSON duplicate keys, unsupported versions, and control messages above 65536 UTF-8 bytes. Validate canonical UUID session references.
- Approvals use a generated one-use, expiring token bound to a SHA-256 digest of the stored request/action plus session revision. The UI supplies only session ID and token; trusted code derives the confirmed action ID. Invalidate tokens on resume, mutation, stop, and process restart.

- [ ] Author tests `test_unknown_control_command_rejected`, `test_oversized_or_duplicate_json_rejected`, `test_approval_bound_to_exact_stored_action`, `test_approval_replay_rejected`, `test_stop_prevents_next_action`, `test_restart_requires_fresh_approval`, and `test_sensitive_history_redacted`.
- [ ] Implement the strict dispatcher, private app-root configuration, single-active-session guard, snapshots, exact approval token store, and independent stop event. Keep all controller mutation on one worker; inspection reads durable state.
- [ ] Advance with `AgentController.step`, not `run_until_stop`, checking Stop before and after each step. Acknowledge pending Stop promptly without claiming the in-flight step has stopped. Reconcile failures and process restart conservatively.
- [ ] Implement a clearly labeled local demo planner for fixed, documented commands such as `Create demo file` and `Show battery`; unsupported goals return blocked. Never imply general natural-language understanding.
- [ ] Deferred verification: `python -m unittest tests.test_app_control -v`; expected contract assertions pass. Preserve failure cases for later execution.

### Task 2: Native Android capability adapters

**Files:**
- Create: `lain/app/native.py`.
- Modify narrowly: `lain/runtime/engine.py` to accept an explicit trusted native adapter dependency while preserving default CLI dispatch.
- Create: `android/app/src/main/java/dev/lain/os/runtime/NativeCapabilities.kt`.
- Test: `tests/test_app_native.py`.

**Interfaces:**
- Consumes: normalized registry arguments and existing `ExecutionOutcome` / `VerificationResult` models.
- Produces: `NativeAndroidAdapter.execute(action: Action) -> ExecutionOutcome` and `verify(action: Action, outcome: ExecutionOutcome) -> VerificationResult`; Kotlin `NativeCapabilities.execute(name: String, argumentsJson: String): String` returns a bounded structured result. Only the trusted runtime dispatches to this adapter.
- Implement the existing five expansion capabilities with platform APIs: structured battery snapshot, bounded vibration, short toast, clipboard write/private comparison, and share chooser. Preserve exact-action Class 2 share policy. Notify and allowed-scheme URI launch stay unsupported until explicit native implementations are present.

- [ ] Author contract tests for approved battery fields only, malformed data rejection, clipboard mismatch redaction, LIMITED UI effects, unsupported native operations, and unchanged default Termux dispatch.
- [ ] Implement closed capability dispatch; UI-bound operations are marshalled to the main looper with bounded waits. Clipboard readback stays inside the adapter and returns only match/mismatch/unavailable. Never select a share receiver.
- [ ] Use existing verification semantics; execution acknowledgement does not prove physical UI effects. Restrict any new manifest permission to implemented functionality.
- [ ] Deferred verification: `python -m unittest tests.test_app_native -v`; real native behavior requires later installed-device acceptance.

### Task 3: Standalone build and private runtime service

**Files:**
- Create: `android/settings.gradle.kts`, `android/build.gradle.kts`, `android/gradle.properties`, `android/app/build.gradle.kts`, wrapper configuration when obtainable.
- Create: `android/app/src/main/AndroidManifest.xml`, `runtime/RuntimeService.kt`, `runtime/RuntimeClient.kt`, and `runtime/RuntimeProtocol.kt` under the Kotlin package.
- Test: `android/app/src/androidTest/java/dev/lain/os/runtime/RuntimeServiceTest.kt`.

**Interfaces:**
- Consumes: Task 1 Python controller and Task 2 native callback.
- Produces: `RuntimeClient.request(command: String, arguments: JSONObject, callback: (JSONObject) -> Unit)` and lifecycle-safe connect/disconnect; private service Binder carries bounded JSON requests and responses.

- [ ] Pin supported Android Gradle/Kotlin/Gradle/Chaquopy versions using current official documentation. Package the repository's `lain` source directly, with no install-time external Python requirement.
- [ ] Implement `RuntimeService` as `exported=false`, `process=:runtime`; authenticate `Binder.getCallingUid() == applicationInfo.uid` before accepting every transaction. Reject unknown transaction codes and excessive message lengths before JSON dispatch.
- [ ] Start Python once in the runtime process. Use one executor for session mutation and a separate authenticated path to signal Stop. Keep progress/results durable and worker scheduling bounded.
- [ ] Keep the service bound while the visible Activity is active. On backgrounding, request cooperative Stop and explain the paused/settling state; do not claim persistent background autonomy or add a foreground-service permission without implementing that lifecycle.
- [ ] Author instrumentation cases for foreign-UID rejection, malformed Binder payloads, reconnect without task replay, and Stop responsiveness. Device execution is deferred.

### Task 4: Human-controlled workbench UI

**Files:**
- Create: `android/app/src/main/java/dev/lain/os/MainActivity.kt`, `ui/WorkbenchState.kt`, `ui/WorkbenchViewModel.kt`.
- Create: `android/app/src/main/res/layout/activity_main.xml`, `res/values/strings.xml`, `res/values/themes.xml`, launcher resources.
- Test: `android/app/src/androidTest/java/dev/lain/os/WorkbenchTest.kt`.

**Interfaces:**
- Consumes: Task 3 `RuntimeClient` and Task 1 redacted snapshots/approval tokens.
- Produces: accessible command entry, Run/Stop controls, progress/results, pending approval card, session history, and clear demo/planner availability indicator.

- [ ] Build the text-first GUI with one active session and bounded, lifecycle-aware polling. Preserve selected session ID across rotation; reconnect and inspect, never automatically resubmit input.
- [ ] Present exact pending action identity and safe arguments; require a separate user tap to approve. Never turn transcript text or planner output into approval. Sensitive payload previews are withheld; original private input remains owner-controlled.
- [ ] Distinguish execution success from PASSED/LIMITED/FAILED verification and Stop requested from Stop completed. Disable repeated submissions while a task is active.
- [ ] Author UI cases for rotation, duplicate taps, stale approvals, unavailable planner, empty input, and sensitive history. Instrumentation execution remains deferred.

### Task 5: APK artifact and honest handoff

**Files:**
- Create: `docs/ANDROID_APP.md`.
- Modify: `.gitignore` only for Android local SDK/build output.

- [ ] Document SDK/JDK/build requirements, fixed offline commands, app-private storage, demo limitations, native support, approval behavior, and pending acceptance.
- [ ] Assemble the debug APK when dependencies are available: `./gradlew --project-dir android :app:assembleDebug`. This is artifact production authorized by the owner, not device verification. Do not run test tasks during this pass.
- [ ] Deliver `android/app/build/outputs/apk/debug/app-debug.apk` if the build succeeds. Otherwise provide source and the exact build blocker; do not substitute a placeholder APK.
- [ ] Report implemented files and deferred tests/security/CI/hardware gates. No claim of release readiness or 1.0 completion. No merge or public publication.

## Plan self-review

The approved interface scope maps to Tasks 1–4; packaging and handoff map to Task 5. The portable CLI retains default adapters. Control authentication, exact approvals, cancellation, redaction, rotation, and unsupported operations have explicit owning tasks and deferred cases. Voice/media/provider/publishing work is excluded from this slice. Native behavior has its own pending hardware gate. The isolated source snapshot and blocked build infrastructure are labeled honestly.
