# LAIN Super-Agent Operator Surface v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the new super-agent goal runtime through the embedded Android control service and a chat-first operator console that can inspect missions, DAG nodes, workers, budgets, events, locks, and audit-visible outcomes without reintroducing constant confirmation prompts.

**Architecture:** Keep the Android app as a private same-UID client of the embedded Python runtime. Add mission-level commands and JSON snapshots to `lain.app.control`, then extend the existing `RuntimeProtocol`, `WorkbenchViewModel`, and `MainActivity` rendering while preserving cold-start inspect-without-replay behavior. This plan depends on the interfaces produced by `2026-10-01-super-agent-core-v1.md`.

**Tech Stack:** Android API 24+, compile/target SDK 35, Kotlin/JVM 17, AndroidX/ViewBinding, Chaquopy Python 3.11, existing Python super-agent core, Android instrumentation tests.

**Spec:** `docs/superpowers/specs/2026-10-01-super-agent-v1-design.md`

## Global Constraints

- This plan starts only after the core plan is green through `python scripts/verify.py`.
- Android `minSdk` remains 24; `compileSdk`/`targetSdk` remain 35; JVM target remains 17.
- The Binder control service remains private to the app UID.
- Cold start/reconnect inspects durable state and never implicitly resumes or replays a mutation.
- Stop/cancel controls remain available independently of ordinary mutation-button state.
- Model output never supplies approval tokens, policy state, resource locks, provenance, or authoritative execution status.
- Private action content stays redacted in snapshots and UI.
- Polling unchanged JSON must not rebuild selectable result/console views.
- No background daemon, AccessibilityService, unrestricted device automation, or voice engine is added here.
- Existing bounded-session demo UI remains available until mission-level tests prove the replacement path.

## Review Focus

- Rotation/reconnect during an active goal must not create a second goal or resume one automatically.
- A large DAG/history response must stay under `RuntimeProtocol.MAX_BYTES`; snapshots need bounded summaries rather than raw transcripts.
- Goal cancellation while workers are settling must show stopping state without claiming all side effects were prevented.
- Private clipboard/share/event content must remain redacted in operator views.
- Old session snapshots and new goal snapshots must be unambiguous during the migration period.

---

### Task 1: Mission-Level Embedded Python Control Commands

**Files:**
- Modify: `lain/app/control.py`
- Create: `tests/test_app_goal_control.py`

**Interfaces:**
- Consumes: `GoalCoordinator`, `GoalStore`, existing `AppController.dispatch`.
- Produces new command names:
  - `goal_start`
  - `goal_list`
  - `goal_inspect`
  - `goal_resume`
  - `goal_cancel`
  - `goal_event`

Add:

```python
def _goal_summary(self, goal: GoalState) -> dict[str, Any]: ...
def _goal_snapshot(self, goal: GoalState) -> dict[str, Any]: ...
```

Snapshot keys are stable:
`goal_id`, `label`, `status`, `active`, `plan_version`, `budget`, `subgoals`, `workers`, `events_pending`, `terminal_reason`, `recovery_required`.

Each subgoal summary contains:
`subgoal_id`, `objective`, `status`, `dependencies`, `worker_profile`, `worker_session_id`, `resource_claims`, `result`.

- [ ] Write failing dispatch/snapshot tests for all six commands.
- [ ] Run `python -m unittest tests.test_app_goal_control -v` and verify red.
- [ ] Implement commands without changing existing session command semantics.
- [ ] Add response-size test that rejects/compacts snapshots before 65536 bytes.
- [ ] Run `python -m unittest tests.test_app_goal_control tests.test_app_control -v`.
- [ ] Commit with `feat: expose goals through embedded app control`.

---

### Task 2: Android Runtime Protocol and ViewModel Mission State

**Files:**
- Modify: `android/app/src/main/java/dev/lain/os/runtime/RuntimeProtocol.kt`
- Modify: `android/app/src/main/java/dev/lain/os/ui/WorkbenchState.kt`
- Modify: `android/app/src/main/java/dev/lain/os/ui/WorkbenchViewModel.kt`
- Modify: `android/app/src/androidTest/java/dev/lain/os/runtime/RuntimeServiceTest.kt`
- Modify: `android/app/src/androidTest/java/dev/lain/os/runtime/RuntimeConnectionTest.kt`

**Interfaces:**
- Read commands add `goal_list`, `goal_inspect`.
- Write commands add `goal_start`, `goal_resume`, `goal_cancel`, `goal_event`.
- `WorkbenchState` adds `goal: JSONObject?` and `goals: JSONArray`.
- Saved-state key becomes `goal_id` for mission mode; do not reuse `session_id`.

- [ ] Add failing protocol allowlist/private-caller tests.
- [ ] Add failing cold-start/rotation tests proving no implicit goal mutation.
- [ ] Implement mission polling and stable change detection.
- [ ] Keep old session polling available behind a compatibility path until Task 4 acceptance.
- [ ] Run Android unit/instrumentation compile target for changed tests.
- [ ] Commit with `feat: bind Android workbench to goal runtime`.

---

### Task 3: Expandable Operator Console Rendering

**Files:**
- Modify: `android/app/src/main/res/layout/activity_main.xml`
- Modify: `android/app/src/main/res/values/strings.xml`
- Modify: `android/app/src/main/java/dev/lain/os/MainActivity.kt`
- Modify: `android/app/src/androidTest/java/dev/lain/os/WorkbenchTest.kt`
- Modify: `android/app/src/androidTest/java/dev/lain/os/RuntimeFlowTest.kt`

**Interfaces:**
- Primary surface remains one free-form goal input plus Run/Stop.
- Add expandable/status sections for:
  - mission status and budget
  - subgoal DAG list
  - workers
  - locks/resource claims
  - recent events
  - action results/audit provenance
- Do not expose a raw JSON editor or approval bypass.

- [ ] Add failing instrumentation assertions for mission title/status, at least three subgoal states, worker profile/session IDs, and budget display.
- [ ] Add redaction test for private payload/event text.
- [ ] Implement rendering with stable view reuse keyed by `goal_id + plan_version + serialized section`.
- [ ] Preserve selectable result text across two unchanged polls.
- [ ] Verify Stop remains enabled while active/recovery state is present.
- [ ] Commit with `feat: add Android super-agent operator console`.

---

### Task 4: Packaged Runtime Acceptance and Migration Switch

**Files:**
- Modify: `android/app/src/androidTest/java/dev/lain/os/RuntimeFlowTest.kt`
- Modify: `android/app/src/androidTest/java/dev/lain/os/WorkbenchTest.kt`
- Modify: `docs/ANDROID_APP.md`
- Modify: `README.md`

**Interfaces:**
- Consumes mission commands/snapshots from Tasks 1-3.
- Produces Android acceptance evidence for the mission path.

- [ ] Add packaged end-to-end test: start goal -> inspect subgoals/workers -> complete -> relaunch -> inspect completed durable goal with no replay.
- [ ] Add cancellation test: active goal -> Stop -> final cancelled/settling state -> no second goal.
- [ ] Run canonical portable verifier: `python scripts/verify.py`.
- [ ] Run Android lint and API-24/API-current instrumentation commands already documented by `docs/ANDROID_APP.md`.
- [ ] If mission acceptance is green, make mission mode the default UI path while retaining old session inspection only for legacy durable sessions.
- [ ] Update docs with current evidence and limitations.
- [ ] Commit with `test: validate Android super-agent mission flow`.

## Self-Review Result

This plan covers the operator-console portion of the approved design without coupling it to core scheduler implementation details. Voice, durable external triggers, and hosted/local provider settings remain independent follow-on surfaces; the UI exposes model/provider usage once the provider-settings work supplies that data, but this plan does not duplicate that subsystem.