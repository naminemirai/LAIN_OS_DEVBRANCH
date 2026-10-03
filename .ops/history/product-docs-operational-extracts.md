# Product-document operational extracts

These passages were removed from product-facing documentation on 2026-10-03 to keep application documentation separate from development operations. They are retained here for engineering context and historical traceability.

Source snapshot: `1b805338b26cd9f089559ddf1bd1244ff0a0ee79`.

## Former README repository-process section

## Repository policy

Do not commit secrets, authentication tokens, private messages, precise personal location history, recovery codes, or other sensitive user data.

Pull requests may merge after a fresh code-review result of **PASS** when no
independent safety or authority blocker remains. Test and acceptance status is
tracked separately: a review pass must never be presented as proof that deferred,
cancelled, or unrun checks passed. Each merge receipt must state those checks as
untested where applicable.

PR #7 (`Android Keystore-backed planner SecretStore`) merged under this policy at
`2946e1a042d57eddffce4477f2136aea4da0ccde`. Review passed on head
`c26925ed76e1e02fd49bd5b7ec796957c36fc423` and Verify workflow #56 succeeded;
Android workflow #45 was cancelled, so its Android instrumentation tests remain
explicitly untested by that merge receipt.

PR #9 merged under this policy at `11906c484ebd91d480178b64728c91684f931115`
after review `5398751890` passed on head
`e0ca01f4bd0f6ee08ee5db500d654a33f038dff8`. The focused contract passed 5/5,
the imported inventory tests passed 4/4, and Verify workflow #72 succeeded.
Android workflow #61 was still in progress at merge time, so it was untested by
the merge decision; it subsequently completed successfully. Repository-native cleanup
`47566d0a87ce06f1ba1e3ca45a7dac37e8bf0232` subsequently removed that imported
orchestration tree from `main`.

## Former Android implementation/evidence history

## Stop scheduling correction

After PR #3 merged, review established a race where Stop could lose its worker
wake-up as an action entered a confirmation pause. Wake-ups now enter the same
single-worker queue as runtime steps, so a Stop arriving during the transition
still settles cancellation. A deterministic JVM regression exercises this case;
the Android workflow runs it alongside APK assembly, lint, and instrumentation.
Version `0.1.4-interface` requires fresh physical acceptance, including Stop at
the confirmation transition. Earlier emulator and Termux evidence does not
certify this changed APK.

## Evidence status for this coding pass

Verification resumed at the owner's request on 2026-10-01. Fresh focused Python
tests passed (19); the canonical suite and Android portable helper each passed
251 tests. APK assembly, instrumentation compilation, and Android lint passed
with Gradle reporting 86 tasks (25 executed, 61 up-to-date). Lint's API 27 theme
attribute was moved out of the API 24 base resources. Android 12+ cloud backup
and device transfer now explicitly exclude application data.

The Android workflow builds both APKs, runs lint, and executes instrumentation
on API 24 and API 35 emulators. The API 24 emulator passed all nine applicable instrumentation tests after
removing an inline theme font-family override that crashed button inflation on
Android 7. The API 26 binding-death callback test runs on newer platforms.
Identical runtime polls no longer rebuild the screen, and unchanged results
preserve selectable text views. The API 24 suite also passed this regression.
Exact CI heads and emulator results are recorded in
[PR #3](https://github.com/null0entry/LAIN_OS_DEVBRANCH/pull/3). Physical acceptance
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
`dev.lain.os`, version `0.1.4-interface` (version code 5), with arm64-v8a and x86_64 support and a
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

## Former voice-suite execution brief

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

## Former voice-suite review/next-action note

## Review and next action

This brief selects a hybrid architecture, one active workflow, user-started voice sessions, stock voices, and a deliberately narrow first video format as proposed defaults. No implementation approval is inferred from those choices. Next: review this written design, then expand F0–F7 into repository-specific implementation steps and verify the current execution environment.

Planning check: baseline conflicts documented; voice and workflow semantics separated; external authority distinct; capability names labeled proposed; all tasks have dependencies and observable acceptance; no code/build/publication completion claims.
