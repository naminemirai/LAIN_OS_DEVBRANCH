# Android interface

The `android/` module is the first standalone LAIN_OS GUI. It embeds the existing
Python package with Chaquopy in a private `:runtime` process; it does not require
Termux, an external Python installation, a server, or a cloud account on the phone.

## Current source scope

- Kotlin/AndroidX text workbench: command entry, Run/Stop, progress and per-action
  execution/verification results, exact-action approval, and recent sessions.
- One active session with existing finite budgets and atomic checkpoints.
- Non-exported bound service, same-UID Binder checks, bounded typed JSON, and an
  independent Stop channel. Backgrounding requests Stop; rotation keeps the
  selected session without submitting another task. This is on-demand execution,
  not a persistent background service.
- Run and approval wait for embedded Python initialization and durable-state
  inspection. Startup failures are distinct from initialization in progress.
  Reconnect inspects existing state; it never replays queued writes. Requests
  and replies from a previous connection cannot migrate into a new binding.
- Native adapters for the five existing expansion capabilities: battery,
  vibration, toast, clipboard write/private comparison, and confirmed share
  chooser. No receiver selection or generic clipboard read is exposed.
- Native notification/URI operations and provider-backed planning remain
  unsupported in this interface. The portable CLI keeps its default adapters.

This version uses a deliberately labeled **offline demo planner**, not a language
model. Choose one of these exact commands:

| Command | Action |
| --- | --- |
| Create demo file | Write `demo.txt` in the app's private workspace; overwrite is not automatic |
| Show battery | Obtain approved structured battery fields |
| Show demo toast | Request a short “Hello from LAIN_OS.” toast |
| Vibrate briefly | Request a 200 ms vibration |
| Copy demo text | Set “Hello from LAIN_OS.” and compare privately |
| Share demo text | Request exact-action confirmation, then open a chooser with “Hello from LAIN_OS.” |

Unknown goals become blocked; they do not launch a shell or arbitrary operation.
During later device testing dismiss the share chooser without sending anything.

## Build a debug APK

Requirements: JDK 17 or 21, Android SDK platform 35 and its build tools, and network
access for the pinned Gradle/AndroidX/Chaquopy dependencies. Android Studio can
open `android/` directly. Configure the local SDK through `ANDROID_HOME` or an
ignored `android/local.properties` file containing `sdk.dir=/absolute/sdk/path`.

From the repository root:

```sh
./android/gradlew --project-dir android :app:assembleDebug
```

The official Gradle wrapper is included. If the default Gradle cache is not
writable, select a writable cache using `GRADLE_USER_HOME`. Keep the execution
environment's proxy and CA trust when downloading dependencies.

Expected artifact after a successful build:
`android/app/build/outputs/apk/debug/app-debug.apk`. A debug APK is not a production
release. No owner release-signing credentials are included. The source bundles
only `lain/`, not repository secrets, session files, or developer configuration.

## Approvals, privacy, and recovery

Approvals are one-use tokens expiring after 120 seconds and bound to the stored
session revision, request ID, and exact action. A planner cannot grant them. Stop,
resume, mutation, and process restart invalidate grants. Sensitive action arguments
are redacted on the interface/history path; clipboard readback stays private.

Data is scoped to the application's private `files/lain` directory. Checkpoints
retain original supplied input and action payloads for trusted recovery, in private
files, as the CLI does. History shows only fixed demo labels and structured results.
Backups and cleartext traffic are disabled; no Internet/microphone/storage permission
is requested by this offline slice. Uninstalling the application removes its
private data through Android's normal behavior.

Stop acknowledges the request while an operation already in flight may settle.
It prevents further steps and records the actual outcome; it does not promise
rollback of an external effect. After process death, the app does not resume or
replay automatically. Select interrupted work and explicitly Resume, approve a
fresh pending action, or Stop it. Existing audit-ahead reconciliation remains
authoritative. Ambiguous requests are never automatically retried.

## Evidence status for this coding pass

Verification resumed at the owner's request on 2026-10-01. Fresh focused Python
tests passed (19); the canonical suite and Android portable helper each passed
251 tests. APK assembly, instrumentation compilation, and Android lint passed
with Gradle reporting 86 tasks (25 executed, 61 up-to-date). Lint's API 27 theme
attribute was moved out of the API 24 base resources. Android 12+ cloud backup
and device transfer now explicitly exclude application data.

The Android workflow builds both APKs, runs lint, and executes instrumentation
on an API 35 emulator. Exact CI heads and emulator results are recorded in
[PR #3](https://github.com/naminemirai/LAIN_OS_DEVBRANCH/pull/3). Physical acceptance
remains open; use [the native APK checklist](ANDROID_DEVICE_ACCEPTANCE.md).
Earlier paused-pass evidence below describes the initial build only.

Source baseline: `main@7abec73ea4bd096b4b6c69cf66745bf6115412e1`. The initial
connector-restored snapshot was moved into a real Git worktree when Git transport
became available: branch `feature/android-interface-v1` in
`/workspace/LAIN_OS_ANDROID_CHECKOUT/.worktrees/android-interface`. Published
history is preserved. The interface and Android CI have been published on that
feature branch in draft PR #3; no merge was performed.

During the initial coding pass, the owner paused verification runs. Python and
Android tests were authored without running them. Verification has now resumed
as recorded above; physical-device acceptance and latency measurement remain open.

After the owner enabled network access, debug APK assembly completed successfully
with Gradle 8.11.1, a full Temurin JDK 17, Android SDK 35/build tools 35.0.0, and the
pinned dependencies. The initial build reported `BUILD SUCCESSFUL in 1m 4s` with 48 tasks
(41 executed, 7 up-to-date). The missing dependency between Python source copying
and merging was corrected in `android/app/build.gradle.kts`.

The output is `android/app/build/outputs/apk/debug/app-debug.apk`; the delivered
copy is `/workspace/artifacts/LAIN_OS-interface-debug.apk`. Its package is
`dev.lain.os`, version `0.1.1-interface` (version code 2), with arm64-v8a and x86_64 support and a
minimum Android API level of 24. It is debug-signed; no release signing was done.
The earlier updated assembly reported `BUILD SUCCESSFUL in 34s`, exit 0, with all
48 tasks executed. Connection regression tests were subsequently compiled along
with the other instrumentation cases.

Maven Central returned HTTP 429 during this build. A local Gradle init script
selected Google's Maven Central mirror without changing dependency versions.
The environment proxy and its CA were preserved. The exact build command and
local setup are recorded in `/workspace/build-evidence/BUILD.md`; the successful
initial log is `/workspace/build-evidence/android-build-0.1.1.log`; resumed build
and lint output is `/workspace/build-evidence/android-validation-build.log`. Early attempts were blocked
by sandbox networking and an installed JRE lacking a compiler; those build
prerequisites were subsequently resolved.

The prior Termux hardware evidence does not certify these new native adapters.
Before claiming this interface usable or merge-ready, install the APK
and complete native adapter, Binder, approval, rotation, interruption, and recovery
acceptance. Verification commands:

```sh
python -m unittest tests.test_app_control tests.test_app_native -v
python scripts/verify.py
./android/gradlew --project-dir android :app:connectedDebugAndroidTest
```

The initial instrumentation cases do not yet cover every device failure contract
in the implementation plan. Full foreign-application IPC rejection, in-flight
rotation/rebind, clipboard restrictions, chooser behavior, stale approvals,
backgrounding races, and measured Stop latency remain device acceptance work.
Voice conversation, media workflows, provider integrations, and YouTube publishing
are later stages of the voice-agent brief.
