# Super-Agent v1 Core Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Extend LAIN_OS's existing durable single-session agent into one persistent top-level goal with a coordinator-managed subgoal DAG, scoped generic workers, deterministic resource locking, durable events, hybrid budgets, and a provider-neutral model-routing boundary.

**Architecture:** Preserve ACTION_PROTOCOL, policy, execution, verification, audit, and existing lain run semantics. Build the new control plane beside lain/agent, reuse AgentController as the initial leaf-worker execution primitive, and introduce parallel scheduling only after persisted DAG and resource-lock behavior are independently tested.

**Tech Stack:** Python 3.11+ standard library, dataclasses/enums/JSON/pathlib, existing LAIN_OS planner/runtime/policy/audit infrastructure, unittest-compatible existing test suite.

**Spec:** docs/superpowers/specs/2026-10-01-super-agent-v1-design.md

## Global Constraints

- One active top-level goal at a time in v1.
- Models propose reasoning; trusted code owns identity, authority, policy, execution, verification, budgets, persistence, locking, and audit.
- Structured durable state outranks transcript history.
- Workers cannot widen delegated authority or budgets.
- Parallel work requires satisfied dependencies and non-conflicting resource claims.
- Mission completion is a coordinator-model decision grounded in verified state.
- Recovery reconciles real state before retrying incomplete work.
- Existing lain run, ACTION_PROTOCOL, policy, verification, and audit behavior must remain compatible.
- No unrestricted background Android control, unconstrained worker swarms, automatic production self-upgrade, or arbitrary self-activating executable code in this milestone.
- Runtime dependencies remain standard-library-only.

## Review Focus

- Corrupt or future-version persisted goal/DAG/event state must fail closed instead of being partially loaded.
- A dependency cycle introduced by planner output must be rejected before any affected node executes.
- Overlapping filesystem/resource claims must serialize even when strings differ syntactically but resolve to the same resource.
- A worker result arriving after cancellation or goal-version change must not silently overwrite newer authoritative state.
- Crash recovery with execution evidence ahead of the coordinator checkpoint must reconcile rather than replay the action.

---

## Task 1: Goal model and hybrid resource envelope

**Files:** create lain/goals/models.py and tests/test_goal_models.py; modify lain/config.py.

**Interfaces:** GoalStatus, GoalBudget, AuthorityEnvelope, Goal; strict to_dict/from_dict; Goal.transition; authority subset/delegation check.

- [ ] Write failing tests for schema version "1", UUID IDs, transitions, finite positive budgets, authority non-expansion, round trips, unknown fields and future versions.
- [ ] Run: python -m unittest tests.test_goal_models tests.test_config -v. Confirm new tests fail for missing interfaces.
- [ ] Implement immutable goal/envelope models and configuration defaults for coordinator iterations, worker calls, total tool calls, runtime, parallel workers and repeated failures.
- [ ] Run focused tests, then python scripts/verify.py; require zero failures.
- [ ] Commit: feat: add durable goal model and budgets

## Task 2: Atomic goal store and single-active-goal invariant

**Files:** create lain/goals/store.py and tests/test_goal_store.py.

**Interfaces:** GoalStore.create, load, save with expected-version guard, list_ids, active_goal_id, and lease/context manager.

- [ ] Write failing tests for atomic save/load, private state permissions where supported, stale-version rejection, refusal of two RUNNING goals, and corrupt/future state failing closed.
- [ ] Run focused tests and confirm failure.
- [ ] Implement by reusing atomic temp-file/fsync/replace and lease patterns from lain/agent/store.py.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: persist top-level goals atomically

## Task 3: Subgoal DAG and deterministic readiness

**Files:** create lain/scheduling/models.py, lain/scheduling/dag.py, tests/test_subgoal_dag.py.

**Interfaces:** SubgoalStatus, ResourceClaim, Subgoal, SubgoalGraph.validate, SubgoalGraph.ready_nodes.

- [ ] Write failing tests for unique IDs, missing/self dependencies, cycles, deterministic READY ordering, dependency failure/cancellation propagation and serialization.
- [ ] Run focused tests and confirm failure.
- [ ] Implement immutable subgoal/resource models with parent goal ID, objective, dependencies, profile, delegated envelopes, claims, state version and result reference.
- [ ] Implement deterministic topological validation; reject cycles before runnable work is returned.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: add persisted subgoal dag model

## Task 4: Resource claims and lock arbitration

**Files:** create lain/scheduling/locks.py and tests/test_resource_locks.py.

**Interfaces:** ResourceLockManager.acquire(owner_id, claims), release(owner_id), conflicts(claims), persisted-lock recovery.

- [ ] Write failing tests for repository conflicts, normalized filesystem path/prefix overlap, external account/service conflicts, exclusive keys, non-conflicts, deterministic acquisition, release after failure and stale recovery.
- [ ] Run focused tests and confirm failure.
- [ ] Implement canonicalization/conflict rules; filesystem claims use resolved paths and prefix semantics.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: serialize conflicting worker resources

## Task 5: Scheduler

**Files:** create lain/scheduling/scheduler.py and tests/test_scheduler.py.

**Interfaces:** Scheduler.select(graph) returning deterministic runnable Subgoals.

- [ ] Write failing tests for dependency ordering, independent parallel selection, max-worker enforcement, conflict serialization, blocked nodes and cancellation propagation.
- [ ] Run focused tests and confirm failure.
- [ ] Implement deterministic selection ordered by explicit priority then stable subgoal ID; scheduler performs no model reasoning.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: schedule dependency-safe subgoals

## Task 6: Generic worker profiles and scoped runtime

**Files:** create lain/workers/models.py, lain/workers/runtime.py, tests/test_worker_runtime.py.

**Interfaces:** WorkerProfile, WorkerAssignment, WorkerResult, WorkerRuntime.run; initial leaf execution reuses AgentController/runtime.

- [ ] Write failing tests proving delegated authority/budget are parent subsets, worker provenance is stable, current single-session execution can act as a leaf worker, and stale/cancelled assignments cannot merge.
- [ ] Run focused tests and confirm failure.
- [ ] Implement profile/assignment/result models; profiles are routing metadata rather than separate agent classes.
- [ ] Implement WorkerRuntime adapter over existing planning/execution while preserving policy and verification authority.
- [ ] Run worker tests, existing agent tests and full verifier.
- [ ] Commit: feat: add scoped generic worker runtime

## Task 7: Provider-neutral model router

**Files:** create lain/models/router.py, tests/test_model_router.py; minimally adapt lain/planning/adapter.py.

**Interfaces:** ModelProfile, ModelRequest, ModelResponse, ModelProvider protocol, ModelRouter.route.

- [ ] Write failing tests for fast, cheap, deep, coding, vision, large-context and private/local profiles; missing profile; provider swapping; credentials absent from model-visible requests.
- [ ] Run focused tests and confirm failure.
- [ ] Implement routing contract with the existing configured subprocess/hosted provider as the first adapter; add no SDK dependency or local inference yet.
- [ ] Run planner/agent regressions and full verifier.
- [ ] Commit: feat: add provider-neutral model routing

## Task 8: Durable event stream and mid-mission control

**Files:** create lain/goals/events.py and tests/test_goal_events.py.

**Interfaces:** GoalEventType, GoalEvent, GoalEventStore.append/read_after.

- [ ] Write failing tests for append-only ordering, monotonic sequence, strict parsing, pause/cancel semantics, goal-version targeting and stale-event rejection.
- [ ] Run focused tests and confirm failure.
- [ ] Implement informational, goal-modification, constraint, priority, pause, resume, cancel and trigger events.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: add durable goal event stream

## Task 9: Coordinator decision protocol

**Files:** create lain/coordinator/models.py, lain/coordinator/planning.py, tests/test_coordinator_planning.py.

**Interfaces:** strict continue/complete/blocked decisions plus bounded subgoal graph mutations and worker-profile requests.

- [ ] Write failing tests for malformed lifecycle output, duplicate IDs, proposed cycles, authority widening, complete with unresolved required nodes, and proposal bounds.
- [ ] Run focused tests and confirm failure.
- [ ] Implement strict parsing/validation; trusted code supplies goal identity/version and validates every graph mutation.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: add coordinator planning protocol

## Task 10: Scoped memory/context construction

**Files:** create lain/memory/context.py and tests/test_super_agent_context.py.

**Interfaces:** build_coordinator_context and build_worker_context.

- [ ] Write failing tests showing verified structured state overrides contradictory transcript text, workers receive scoped DAG/context, sensitive arguments remain redacted, and compaction retains evidence references.
- [ ] Run focused tests and confirm failure.
- [ ] Implement bounded context assembly using existing redaction; semantic retrieval remains an explicit interface backed only by stored references in this milestone.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: build scoped super-agent context

## Task 11: Coordinator lifecycle controller

**Files:** create lain/coordinator/controller.py and tests/test_coordinator_controller.py.

**Interfaces:** CoordinatorController.create_goal, step, run_until_stop, pause, resume, cancel.

- [ ] Write failing lifecycle tests for create -> decompose -> dispatch -> merge -> replan -> complete, worker failure -> alternate replan, budget blocking, pause/cancel and goal modification/version increment.
- [ ] Add stale-result test: worker output from version N is refused after authoritative state advances to N+1.
- [ ] Run focused tests and confirm failure.
- [ ] Implement sequential coordinator first: one READY worker per step, durable checkpoint around dispatch, verified result merge, coordinator-model completion.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: coordinate durable hierarchical goals

## Task 12: Recovery and reconciliation

**Files:** modify coordinator controller or add a focused reconciliation helper; create tests/test_coordinator_recovery.py.

**Interfaces:** reconcile(goal_id) before resumed scheduling.

- [ ] Write failing tests for crash before dispatch, during action, execution/audit ahead of checkpoint, checkpoint complete with worker lost, stale locks and paused/blocked restart.
- [ ] Run focused tests and confirm failure.
- [ ] Generalize existing agent-session evidence checks; never replay solely because coordinator state is behind.
- [ ] Run recovery tests, existing agent recovery tests and full verifier.
- [ ] Commit: feat: reconcile super-agent state after restart

## Task 13: Safe parallel worker execution

**Files:** modify coordinator controller and scheduler; create tests/test_parallel_workers.py.

- [ ] Write failing tests proving independent workers may overlap, conflicting claims never overlap, merges are deterministic, one failure cannot corrupt siblings, and cancellation prevents new dispatch.
- [ ] Run focused tests and confirm failure.
- [ ] Add bounded standard-library concurrency up to max_parallel_workers; serialize authoritative state/checkpoint merges.
- [ ] Run focused tests repeatedly for race flakiness, then full verifier.
- [ ] Commit: feat: run independent subgoals concurrently

## Task 14: Provenance expansion

**Files:** modify existing audit model/logger discovered during implementation; create tests/test_super_agent_audit.py.

- [ ] Write failing tests requiring goal ID, subgoal ID, worker ID and plan version on consequential worker actions while preserving sensitive-data redaction.
- [ ] Run focused tests and confirm failure.
- [ ] Extend audit records compatibly; retain legacy record loading where existing behavior requires it.
- [ ] Run audit/runtime/agent regressions and full verifier.
- [ ] Commit: feat: trace actions to super-agent provenance

## Task 15: Durable trigger boundary

**Files:** create lain/triggers/models.py, lain/triggers/dispatcher.py, tests/test_triggers.py.

- [ ] Write failing tests proving schedule/webhook/state-change/condition/standing-goal triggers create events but cannot bypass policy, invent unrelated missions or activate unconfigured capabilities.
- [ ] Run focused tests and confirm failure.
- [ ] Implement only typed durable trigger dispatch; no unrestricted daemon or provider-specific webhook server yet.
- [ ] Run focused tests and full verifier.
- [ ] Commit: feat: add authorized durable trigger boundary

## Task 16: CLI compatibility and operator surface

**Files:** modify lain/cli.py; create tests/test_super_agent_cli.py; regress tests/test_agent_cli.py and tests/test_cli.py.

- [ ] Write failing tests for goal create/run/status/event/pause/resume/cancel, JSON state, invalid IDs/events and existing agent-command compatibility.
- [ ] Run focused tests and confirm failure.
- [ ] Wire CLI to CoordinatorController without silently changing legacy semantics.
- [ ] Run CLI regressions and full verifier.
- [ ] Commit: feat: expose super-agent goal controls

## Task 17: End-to-end super-agent proof

**Files:** create tests/test_super_agent_end_to_end.py and update docs only for verified behavior.

- [ ] Test a goal decomposed into at least two independent safe filesystem subgoals plus one dependent subgoal; require verification-fed state, coordinator completion and queryable provenance.
- [ ] Add recovery case after verified execution but before coordinator merge; assert no duplicate side effect.
- [ ] Add mid-mission constraint event; assert version increment and replanning without implicit cancellation.
- [ ] Run focused E2E tests, then python scripts/verify.py; require zero failures.
- [ ] Commit: test: prove super-agent goal lifecycle end to end

## Task 18: Android operator-console integration

**Files:** inspect and modify the existing android application bridge/view-model/state files; add tests in the existing Android test layout; update docs/ANDROID_APP.md.

- [ ] Map the existing Android state bridge and write failing parsing/rendering tests for goal state and pause/resume/cancel.
- [ ] Add read-only goal, DAG, worker, lock, budget and blocker panels first.
- [ ] Route control events through the trusted runtime boundary; UI never edits persisted goal files directly.
- [ ] Run repository verifier and all documented Android lint/unit/instrumentation checks; record physical-device-only acceptance separately.
- [ ] Commit: feat: expose super-agent operator console on android

## Final Verification

- [ ] Run python scripts/verify.py from a clean worktree.
- [ ] Run the complete Android verification documented by the repository.
- [ ] Confirm git diff --check is clean.
- [ ] Confirm no secrets, credentials, private transcript content or generated runtime state are tracked.
- [ ] Confirm legacy lain run and direct ACTION_PROTOCOL execution still pass existing tests.
- [ ] Review the branch against every acceptance criterion in the design spec.
- [ ] Perform whole-branch code review before merge.
