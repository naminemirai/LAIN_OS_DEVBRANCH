# Autonomous Loops v1 Implementation Plan

**Goal:** Add a durable, resumable, bounded autonomous agent runtime that repeatedly plans bounded action batches, executes them through the existing trusted runtime, checkpoints after every action, and stops in an explicit terminal or paused state.

**Architecture:** Keep one-shot planning and direct ACTION_PROTOCOL execution intact. Add an agent-specific planner lifecycle contract and a new `lain.agent` package above `PlanningService`/`RuntimeEngine`; the controller advances a persisted state machine one safe transition at a time, while `RuntimeEngine` gains a reusable single-action execution entry point so per-action checkpoints do not duplicate policy, audit, verification, or idempotency logic. Session state is atomically persisted under the audit directory's sibling `sessions/` directory, which resolves to `~/.lain/sessions` for the default config and remains isolated under `--workspace` in tests.

**Tech Stack:** Python 3.11+, standard library only at runtime, `unittest`, existing LAIN_OS ACTION_PROTOCOL/runtime/audit stack, POSIX `fcntl.flock` for Linux/Termux session execution locking.

**Spec:** `docs/specs/2026-09-29-autonomous-loops-v1-design.md`

## Global Constraints

- Each planner iteration may return up to the configured planner action limit.
- State writes MUST be atomic: write a complete temporary file in the same directory, flush it, then replace the previous state file.
- Default v1 budgets are `max_iterations = 12`, `max_actions_per_batch = planner_max_actions`, `max_total_actions = 32`, and `max_runtime_seconds = 900`.
- Resuming a session does not reset consumed budgets.
- Actions recorded as successfully executed and verified are never replayed.
- External writes whose outcome is ambiguous remain non-retriable under the existing external-write idempotency rule.
- The planner cannot mark its own action confirmed and cannot convert a confirmation-required result into a retry.
- No configuration value may represent "unlimited" in v1.
- Autonomous Loops v1 does not add persistent background execution, scheduled wakeups, unrestricted AccessibilityService automation, arbitrary shell, arbitrary HTTP, self-modifying policy, multi-node execution, or hidden execution.
- The existing capability registry, policy engine, confirmation rules, deterministic executors, verification, audit, and request/action idempotency remain authoritative.
- Existing `lain plan`, `lain do`, `lain execute`, and ACTION_PROTOCOL behavior must remain backward compatible.
- Runtime dependencies remain standard-library-only.

## Review Focus

1. **Concurrent resume of the same session:** a second controller must fail with `AGENT_SESSION_BUSY` before planner or executor work; Task 4 adds lock contention tests and Task 6 proves the controller holds the lease across a whole run.
2. **Crash after audit/execution but before session checkpoint:** a resumed stale checkpoint must never replay that action; Task 3 adds per-action audit idempotency and Task 6 tests the resulting fail-closed blocked state.
3. **Wrong confirmation ID while paused:** no action executes and the session remains `paused_confirmation`; Task 6 and Task 7 pin this behavior.
4. **Malformed/corrupt/path-traversal session lookup:** reject before filesystem escape or action execution; Task 4 tests UUID validation, corrupt JSON, and unsupported schema versions.
5. **Resume of terminal or budget-exhausted session:** no planner or runtime call occurs; Task 6 tests all terminal states and budget exhaustion before the next side effect.

---

### Task 1: Add the autonomous planner lifecycle contract without breaking one-shot planning

**Files:**
- Modify: `lain/planning/models.py`
- Modify: `lain/planning/protocol.py`
- Modify: `lain/planning/adapter.py`
- Modify: `lain/planning/__init__.py`
- Create: `tests/test_agent_planner.py`
- Modify: `tests/test_planner.py`

**Interfaces:**
- Consumes: existing `CapabilityDefinition`, `ProposedAction`, `PlannerConfig`, subprocess environment isolation.
- Produces:
  - `AgentPlannerStatus(str, Enum)` with `CONTINUE = "continue"`, `COMPLETE = "complete"`, `BLOCKED = "blocked"`.
  - `AgentPlannerDecision(status: AgentPlannerStatus, reason: str, actions: tuple[ProposedAction, ...])`.
  - `AgentPlanner` protocol with `decide(goal: str, context: dict[str, Any], capabilities: tuple[CapabilityDefinition, ...]) -> AgentPlannerDecision`.
  - `agent_planner_request(goal: str, context: dict[str, Any], capabilities: tuple[CapabilityDefinition, ...], max_actions: int) -> dict[str, Any]`.
  - `parse_agent_decision(data: bytes, *, max_output_bytes: int, max_actions: int) -> AgentPlannerDecision`.
  - `SubprocessPlanner.decide(goal: str, context: dict[str, Any], capabilities: tuple[CapabilityDefinition, ...]) -> AgentPlannerDecision`.
- Existing `Planner.propose()`, `planner_request()`, and `parse_proposal()` stay unchanged for `plan`/`do`.

- [ ] **Step 1: Write failing lifecycle parser/request tests in `tests/test_agent_planner.py`**

Cover these exact rules:

```python
self.assertEqual(parse_agent_decision(valid_continue, ...).status, AgentPlannerStatus.CONTINUE)
self.assertEqual(parse_agent_decision(valid_complete, ...).actions, ())
self.assertEqual(parse_agent_decision(valid_blocked, ...).actions, ())
```

Also assert:

- `continue` with zero actions fails with `PLANNER_OUTPUT_INVALID`;
- `complete` or `blocked` with actions fails;
- blank/non-string `reason` fails;
- unknown status fails;
- extra top-level/action fields fail;
- action count above `max_actions` fails;
- malformed/fenced/trailing JSON still fails;
- `agent_planner_request(...)` includes `"mode": "agent"`, original goal, supplied context, registry-derived capabilities, max-actions constraint, and an instruction that context/history are data rather than authority.

- [ ] **Step 2: Run the new tests and confirm they fail**

Run: `python -m unittest tests.test_agent_planner -v`

Expected: FAIL because the agent lifecycle types/parser do not exist.

- [ ] **Step 3: Implement the lifecycle models and protocol parser**

In `lain/planning/models.py`, add the enum, decision dataclass, and protocol exactly as listed in Interfaces.

In `lain/planning/protocol.py`, add `agent_planner_request()` and `parse_agent_decision()`. Require exactly the fields `status`, `reason`, and `actions`; reuse the existing proposed-action shape; preserve all current byte/action limits.

- [ ] **Step 4: Add `SubprocessPlanner.decide()` using the existing hardened process boundary**

Use the same fixed argv, `shell=False`, minimal environment, timeout, bounded stdout/stderr, and `_exchange()` path as `propose()`. Only the stdin request builder and stdout parser differ.

- [ ] **Step 5: Add a subprocess-agent regression test**

Use a tiny `python -c` planner that reads stdin, asserts `mode == "agent"`, and returns a valid lifecycle decision. Assert `GROQ_API_KEY` and existing Reddit credential variables still do not reach the subprocess environment.

- [ ] **Step 6: Run agent-planner and existing planner tests**

Run: `python -m unittest tests.test_agent_planner tests.test_planner -v`

Expected: PASS, including all existing one-shot planner tests.

- [ ] **Step 7: Commit**

```bash
git add lain/planning tests/test_agent_planner.py tests/test_planner.py
git commit -m "feat: add autonomous planner lifecycle contract"
```

---

### Task 2: Add agent budget configuration and durable domain models

**Files:**
- Modify: `lain/config.py`
- Modify: `lain/errors.py`
- Create: `lain/agent/__init__.py`
- Create: `lain/agent/models.py`
- Modify: `tests/test_config.py`
- Create: `tests/test_agent_models.py`

**Interfaces:**
- Consumes: `RuntimeConfig`, `PlannerConfig.max_actions`, protocol `Action`/`ActionResult`, `AgentPlannerStatus`.
- Produces:
  - `AgentConfig(max_iterations: int = 12, max_total_actions: int = 32, max_runtime_seconds: float = 900.0)`.
  - `RuntimeConfig.agent: AgentConfig`.
  - TOML keys `agent_max_iterations`, `agent_max_total_actions`, `agent_max_runtime_seconds`.
  - `AgentSessionStatus`: `created`, `planning`, `executing`, `paused_confirmation`, `blocked`, `complete`, `cancelled`, `budget_exhausted`, `failed`.
  - `AgentBudget(max_iterations: int, max_actions_per_batch: int, max_total_actions: int, max_runtime_seconds: float)`.
  - `AgentActionRecord(action: Action, result: ActionResult | None)`.
  - `AgentIterationRecord(number: int, planner_status: AgentPlannerStatus, planner_reason: str, request_id: str | None, actions: tuple[AgentActionRecord, ...])`.
  - `AgentSession(version: str, session_id: str, goal: str, status: AgentSessionStatus, created_at: str, updated_at: str, iterations: tuple[AgentIterationRecord, ...], total_attempted_actions: int, budget: AgentBudget, cumulative_runtime_seconds: float, terminal_reason: str | None)`.
  - `AgentSession.to_dict() -> dict[str, Any]`, `AgentSession.from_dict(raw: dict[str, Any]) -> AgentSession`, and `AgentSession.transition(...)`.
  - New structured error codes: `AGENT_SESSION_NOT_FOUND`, `AGENT_SESSION_INVALID`, `AGENT_SESSION_BUSY`, `AGENT_STATE_INVALID`.

- [ ] **Step 1: Write failing config tests**

Assert defaults are exactly 12, 32, and 900.0; TOML overrides load; zero/negative values fail; no unlimited sentinel such as 0 or -1 is accepted.

- [ ] **Step 2: Write failing model round-trip and transition tests**

Assert:

- a newly constructed session serializes and deserializes without loss;
- `iteration_count` is derived from `len(iterations)`;
- action/result enums survive round-trip;
- terminal states reject every further transition;
- invalid transitions such as `created -> complete` and `paused_confirmation -> planning` fail with `AGENT_STATE_INVALID`;
- allowed transitions match the spec state machine.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `python -m unittest tests.test_config tests.test_agent_models -v`

Expected: FAIL on missing config/model types.

- [ ] **Step 4: Implement `AgentConfig` and config parsing**

Keep planner config separate. Construct `RuntimeConfig.agent` from the three flat TOML keys so existing config files remain valid without a nested-table migration.

- [ ] **Step 5: Implement the session domain model and transition table**

Use frozen/slotted dataclasses. Set persisted session schema version to `"1"`. For a `continue` iteration, require a UUID request ID and at least one action; for `complete`/`blocked`, require no request ID and no actions.

- [ ] **Step 6: Run focused tests**

Run: `python -m unittest tests.test_config tests.test_agent_models -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lain/config.py lain/errors.py lain/agent tests/test_config.py tests/test_agent_models.py
git commit -m "feat: add autonomous session model and budgets"
```

---

### Task 3: Extract a trusted per-action runtime execution boundary

**Files:**
- Modify: `lain/audit/logger.py`
- Modify: `lain/runtime/engine.py`
- Modify: `tests/test_audit.py`
- Modify: `tests/test_runtime.py`
- Modify: `tests/test_reddit.py`

**Interfaces:**
- Consumes: existing `ActionEnvelope`, preflight, policy, executor, verifier, and audit methods.
- Produces:
  - `AuditLogger.has_executed_action(request_id: str, action_id: str) -> bool`.
  - `RuntimeEngine.execute_action(envelope: ActionEnvelope, action_id: str, *, confirmed_action_ids: frozenset[str] = frozenset()) -> ActionResult`.
  - private shared execution helper used by both `execute()` and `execute_action()`.
- `RuntimeEngine.execute()` keeps its existing request-level duplicate guard and stop-on-first-failure behavior.

- [ ] **Step 1: Write failing per-action runtime tests**

Use one two-action envelope and assert:

```python
first = engine.execute_action(req, "a1")
second = engine.execute_action(req, "a2")
self.assertEqual(first.status, ActionStatus.SUCCESS)
self.assertEqual(second.status, ActionStatus.SUCCESS)
```

Also assert:

- re-running `a1` raises `DUPLICATE_REQUEST`;
- unknown action ID raises `ARGUMENT_INVALID`;
- all actions are preflighted before the selected action executes;
- confirmation-required `a1` can be retried with `confirmed_action_ids={"a1"}` because the first policy check did not execute it.

- [ ] **Step 2: Add the audit-level action-idempotency test**

Create audit records for `request_id=r1`, action `a1` attempted and `a2` not attempted. Assert `has_executed_action("r1", "a1")` is true and `a2` is false.

- [ ] **Step 3: Add the ambiguous external-write regression**

With the fake Reddit transport/client, force an external-write attempt to reach the pre-submit audit barrier and then return an ambiguous failure. A second `execute_action()` call for that same request/action must raise `DUPLICATE_REQUEST` and must not call the transport again.

- [ ] **Step 4: Run focused tests and confirm failure**

Run: `python -m unittest tests.test_audit tests.test_runtime tests.test_reddit -v`

Expected: FAIL on missing per-action methods.

- [ ] **Step 5: Refactor `RuntimeEngine` without changing direct execution behavior**

Extract the current policy → optional external barrier → executor → verifier → audit sequence into one private helper. `execute()` loops over that helper as today. `execute_action()` preflights, finds the exact action, applies `has_executed_action()`, and invokes the same helper.

Do not move policy or execution logic into the future agent controller.

- [ ] **Step 6: Run focused and end-to-end regression tests**

Run: `python -m unittest tests.test_audit tests.test_runtime tests.test_reddit tests.test_end_to_end -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lain/audit/logger.py lain/runtime/engine.py tests/test_audit.py tests/test_runtime.py tests/test_reddit.py
git commit -m "refactor: expose idempotent per-action runtime execution"
```

---

### Task 4: Add atomic session storage and exclusive session leases

**Files:**
- Create: `lain/agent/store.py`
- Create: `tests/test_agent_store.py`

**Interfaces:**
- Consumes: `AgentSession.from_dict()`/`to_dict()`, `LainError`.
- Produces:
  - `AgentSessionStore(root: Path)`.
  - `path_for(session_id: str) -> Path`.
  - `save(session: AgentSession) -> None`.
  - `load(session_id: str) -> AgentSession`.
  - `list_sessions() -> tuple[AgentSession, ...]` sorted newest-updated first.
  - `lease(session_id: str)` context manager holding a non-blocking exclusive `fcntl.flock` until exit.
- Session IDs are UUIDs; invalid IDs fail with `AGENT_SESSION_INVALID`.
- Lock contention fails with `AGENT_SESSION_BUSY`.

- [ ] **Step 1: Write failing persistence tests**

Assert saving creates:

```text
<root>/<session-id>/state.json
```

and loading returns the same model. Assert list ordering by `updated_at`.

- [ ] **Step 2: Write atomicity/permissions tests**

Patch `os.replace` to fail and assert the old valid `state.json` remains readable. Assert state file mode is `0600` and session directory is not world/group accessible.

- [ ] **Step 3: Write fail-closed lookup tests**

Assert:

- `../../escape` and non-UUID IDs raise `AGENT_SESSION_INVALID`;
- missing UUID raises `AGENT_SESSION_NOT_FOUND`;
- malformed JSON, wrong shape, and unsupported schema version raise `AGENT_SESSION_INVALID`;
- no action/controller code is involved in these failures.

- [ ] **Step 4: Write the concurrent-lease regression**

Hold `store.lease(session_id)` in one context and assert a second lease attempt raises `AGENT_SESSION_BUSY`. After the first context exits, acquiring again succeeds; this proves process death/descriptor close does not require deleting a stale lock file.

- [ ] **Step 5: Run tests and confirm failure**

Run: `python -m unittest tests.test_agent_store -v`

Expected: FAIL because the store does not exist.

- [ ] **Step 6: Implement atomic storage and POSIX locking**

Write a complete temp file in the target session directory, flush and `os.fsync()` it, `os.replace()` onto `state.json`, then fsync the directory where supported. Use `fcntl.flock(fd, LOCK_EX | LOCK_NB)` for the lease.

- [ ] **Step 7: Run store tests**

Run: `python -m unittest tests.test_agent_store -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add lain/agent/store.py tests/test_agent_store.py
git commit -m "feat: add durable autonomous session store"
```

---

### Task 5: Build redacted planner context and trusted agent planning service

**Files:**
- Create: `lain/agent/context.py`
- Create: `lain/agent/planning.py`
- Modify: `lain/agent/__init__.py`
- Create: `tests/test_agent_context.py`
- Create: `tests/test_agent_planning.py`

**Interfaces:**
- Consumes: `AgentSession`, `AgentPlanner`, `AgentPlannerDecision`, `CapabilityRegistry`, existing `redact()`.
- Produces:
  - `build_agent_context(session: AgentSession) -> dict[str, Any]`.
  - `AgentPlanningService(planner: AgentPlanner, *, registry: CapabilityRegistry = DEFAULT_REGISTRY, max_actions: int = 8)`.
  - `AgentPlanningService.decide(goal: str, context: dict[str, Any], iteration_number: int) -> AgentIterationRecord`.
- For `continue`, trusted IDs are `i{iteration_number}a{1-based-index}` and the trusted layer creates a fresh UUID request ID.
- For `complete`/`blocked`, the resulting iteration has no request ID and no actions.

- [ ] **Step 1: Write failing context tests**

Build a session containing prior actions/results and assert context includes:

- original goal;
- iteration count;
- remaining iteration/action/runtime budgets;
- prior planner statuses/reasons;
- action type;
- redacted arguments;
- result status;
- verification status and redacted non-secret details.

Assert keys such as `token`, `authorization`, `body`, and `content` are replaced by `"[REDACTED]"` before planner context leaves the trusted layer.

- [ ] **Step 2: Write failing trusted-planning tests**

With a fake `AgentPlanner`, assert a `continue` decision becomes an `AgentIterationRecord` whose actions have IDs `i1a1`, `i1a2`, whose request ID is generated locally, and whose arguments pass the trusted capability validator.

Also assert unknown capabilities, invalid arguments, fake malformed decision objects, and action counts above the service limit fail before execution.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `python -m unittest tests.test_agent_context tests.test_agent_planning -v`

Expected: FAIL on missing modules.

- [ ] **Step 4: Implement `build_agent_context()`**

Use the existing recursive `redact()` helper for action arguments and result/verification details. Do not include audit logs, environment variables, credentials, or local policy internals.

- [ ] **Step 5: Implement `AgentPlanningService.decide()`**

Call `planner.decide()`, re-check lifecycle invariants even for injected planners, validate every proposed capability/argument through the trusted registry, assign trusted IDs/UUID, and return the immutable iteration record.

- [ ] **Step 6: Run focused tests**

Run: `python -m unittest tests.test_agent_context tests.test_agent_planning -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lain/agent tests/test_agent_context.py tests/test_agent_planning.py
git commit -m "feat: add trusted autonomous planning context"
```

---

### Task 6: Implement the durable autonomous controller state machine

**Files:**
- Create: `lain/agent/controller.py`
- Modify: `lain/agent/__init__.py`
- Create: `tests/test_agent_controller.py`

**Interfaces:**
- Consumes: `AgentPlanningService`, `RuntimeEngine.execute_action()`, `AgentSessionStore`, `AgentBudget`, `build_agent_context()`.
- Produces:
  - `AgentController(planning, runtime, store, default_budget, *, monotonic_clock=time.monotonic, now=utc_now)`.
  - `create(goal: str) -> AgentSession`.
  - `step(session_id: str, *, confirmed_action_ids: frozenset[str] = frozenset()) -> AgentSession`.
  - `run_until_stop(session_id: str, *, confirmed_action_ids: frozenset[str] = frozenset()) -> AgentSession`.
  - `cancel(session_id: str) -> AgentSession`.
- `step()` advances exactly one planner decision or one action execution/checkpoint. `run_until_stop()` holds one session lease across the whole invocation and repeatedly calls a private unlocked step until a terminal state or `paused_confirmation`.

- [ ] **Step 1: Write the ordinary autonomous-loop test**

Fake planner sequence:

1. `continue` with two safe file actions;
2. `complete` with no actions.

Assert `run_until_stop()` creates two files through the real `RuntimeEngine`, records both successful results, checkpoints them, performs the second planning iteration, and ends `complete`.

- [ ] **Step 2: Write the bounded-batch stop tests**

For each runtime result class, assert later actions in the same batch never execute:

- `CONFIRMATION_REQUIRED` -> `paused_confirmation`;
- `DENIED` -> `blocked`;
- `UNSUPPORTED` -> `blocked`;
- `FAILURE` or verification failure -> `failed`.

A successful action advances to the next batch action; the last successful action transitions back to `planning`.

- [ ] **Step 3: Write the per-action interruption/resume integration test**

Drive the controller manually:

```python
session = controller.create(goal)
controller.step(session.session_id)   # planner -> executing batch
controller.step(session.session_id)   # action 1 -> checkpoint
```

Construct a fresh controller/store instance, resume the same session, and assert action 1 is not executed again, action 2 executes once, the next planner decision is `complete`, and the session ends `complete`.

- [ ] **Step 4: Write the audit-ahead-of-checkpoint crash regression**

Simulate a stale session checkpoint where the current action has no stored result but `AuditLogger.has_executed_action(request_id, action_id)` is already true. Resume must not replay. It must transition fail-closed to `blocked` with a reconciliation-required terminal reason.

- [ ] **Step 5: Write confirmation resume tests**

Assert a paused action:

- stays paused and executes nothing when resumed without `--confirm`;
- stays paused and executes nothing for the wrong action ID;
- with the exact `iNaM` confirmation ID, reuses the same trusted request/action IDs, executes once, replaces the session's confirmation-required result with success, checkpoints, and continues.

- [ ] **Step 6: Write cancellation and terminal-resume tests**

Assert `cancel()` persists `cancelled` and never rolls back completed work. Assert `step()`/`run_until_stop()` on `complete`, `blocked`, `cancelled`, `budget_exhausted`, or `failed` never call planner/runtime and raise `AGENT_STATE_INVALID` or return the unchanged terminal session according to one consistent documented behavior; choose **raise `AGENT_STATE_INVALID` for explicit resume/step attempts**.

- [ ] **Step 7: Write budget tests with an injected clock**

Assert:

- planner is not called once 12 iterations are consumed;
- runtime is not called once 32 attempted actions are consumed;
- `planner.max_actions` is persisted as `max_actions_per_batch`;
- cumulative active runtime persists across controller reconstruction;
- at or above 900 seconds, the next planner/executor side effect is prevented and state becomes `budget_exhausted`;
- confirmation-required and denied policy decisions do not increment `total_attempted_actions`; success/failure/unsupported executions do.

- [ ] **Step 8: Write the concurrent-controller test**

Hold one `run_until_stop()` session lease and attempt a second controller operation against the same ID. Assert `AGENT_SESSION_BUSY` occurs before planner or runtime calls.

- [ ] **Step 9: Run controller tests and confirm failure**

Run: `python -m unittest tests.test_agent_controller -v`

Expected: FAIL because the controller does not exist.

- [ ] **Step 10: Implement the state machine**

Persist `planning` before invoking the planner. Persist the full trusted `continue` batch before executing its first action. After every runtime result, update that action record and save before another action can execute.

Measure each planner/executor call with the injected monotonic clock and add elapsed time to the session before its next checkpoint.

Catch `DUPLICATE_REQUEST` from a stale current action as a reconciliation condition; do not ask the runtime to retry it and do not infer success from the stale session.

- [ ] **Step 11: Run controller tests**

Run: `python -m unittest tests.test_agent_controller -v`

Expected: PASS.

- [ ] **Step 12: Commit**

```bash
git add lain/agent/controller.py lain/agent/__init__.py tests/test_agent_controller.py
git commit -m "feat: add durable autonomous loop controller"
```

---

### Task 7: Expose autonomous sessions through the CLI

**Files:**
- Modify: `lain/cli.py`
- Create: `tests/test_agent_cli.py`

**Interfaces:**
- Consumes: `RuntimeConfig.agent`, `SubprocessPlanner`, `AgentPlanningService`, `RuntimeEngine`, `AgentSessionStore`, `AgentController`.
- Produces CLI commands:
  - `lain run "<goal>" [--json]`
  - `lain sessions [--json]`
  - `lain session <session-id> [--json]`
  - `lain resume <session-id> [--confirm <action-id>]... [--json]`
  - `lain cancel <session-id> [--json]`
- Default session root is `config.audit_path.parent / "sessions"`; with the default config this is `~/.lain/sessions`, and with `--workspace /tmp/x` it is `/tmp/x/.lain/sessions`.

- [ ] **Step 1: Write failing CLI parser/output tests**

Use a subprocess planner script that switches on `request["mode"] == "agent"` and the supplied context:

- first planner turn returns a two-file `continue` batch;
- second planner turn returns `complete`.

Write a temporary TOML config whose `allowed_roots` point at `<tmp>/workspace`, whose `audit_path` is `<tmp>/.lain/audit.jsonl`, and whose `planner_command` is the fake subprocess planner. Assert `lain --config <config> run "..." --json` returns a complete session and creates the session state under `<tmp>/.lain/sessions`.

- [ ] **Step 2: Add sessions/session/cancel tests**

Assert `sessions --json` lists saved sessions, `session <id> --json` returns the full redacted-safe session model, and `cancel <id> --json` persists `cancelled`.

- [ ] **Step 3: Add paused-confirmation CLI tests**

Use an overwrite action requiring confirmation. Assert:

- `run` returns the session as `paused_confirmation` without mutation;
- `resume <id>` without confirmation does not mutate;
- `resume <id> --confirm wrong-id` does not mutate;
- `resume <id> --confirm i1a1` executes and allows the session to continue.

- [ ] **Step 4: Preserve existing CLI regression behavior**

Run existing `tests.test_cli` and `tests.test_planner_cli`; `plan`, `do`, `execute`, `audit`, and `capabilities` output and exit behavior must remain unchanged.

- [ ] **Step 5: Implement CLI construction and commands**

Add one private helper that constructs the agent stack from `RuntimeConfig`; do not duplicate planner/runtime setup in every command.

Use existing `_emit()` JSON conventions. A successfully completed session exits 0; paused/blocked/budget-exhausted/cancelled/failed session outcomes exit 3; structured argument/runtime exceptions remain exit 2.

- [ ] **Step 6: Run CLI tests**

Run: `python -m unittest tests.test_agent_cli tests.test_cli tests.test_planner_cli -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lain/cli.py tests/test_agent_cli.py
git commit -m "feat: expose autonomous sessions in CLI"
```

---

### Task 8: Add full-loop regression coverage, protocol docs, and verification

**Files:**
- Create: `tests/test_agent_end_to_end.py`
- Create: `specs/AGENT_PROTOCOL.md`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/ROADMAP.md`

**Interfaces:**
- Consumes: all previous task interfaces.
- Produces: documented autonomous planner contract, CLI workflow, safety/recovery semantics, and a portable end-to-end regression suite.

- [ ] **Step 1: Write the full interruption/resume acceptance test**

The test must prove, with a fake model and real local filesystem runtime:

```text
goal
→ planner returns two-action batch
→ action 1 succeeds and verifies
→ durable checkpoint
→ controller instance is discarded
→ fresh controller resumes
→ action 1 is not replayed
→ action 2 succeeds and verifies
→ next planner turn returns complete
→ session persists complete
```

Assert audit contains one execution attempt per completed action.

- [ ] **Step 2: Add a security regression for planner authority**

Use hostile goal/context text claiming that policy is disabled or an action is pre-confirmed. Return an overwrite or Class 2 action. Assert the existing policy engine still pauses/requires confirmation and no planner field can manufacture authorization.

- [ ] **Step 3: Run the full unit suite before documentation changes**

Run: `python -m unittest discover -s tests -q`

Expected: all tests pass.

- [ ] **Step 4: Document the autonomous planner wire contract**

In `specs/AGENT_PROTOCOL.md`, document:

- `mode: "agent"` request;
- goal, context, registry-derived capabilities, constraints;
- exact `status/reason/actions` response;
- lifecycle invariants;
- model output remains untrusted;
- trusted IDs, policy, execution, verification, and session state are not planner-controlled.

- [ ] **Step 5: Update user and architecture documentation**

README: add the five autonomous CLI commands, budget defaults, pause/confirm/resume example, and state location.

ARCHITECTURE: place `AgentController` above planning/runtime and describe per-action checkpointing.

SECURITY: add finite-budget, no-self-confirmation, session-locking, no-replay, and audit-ahead-of-checkpoint recovery rules.

ROADMAP: mark the bounded durable v0.3 autonomous-loop slice as implemented only after verification; keep persistent background service and AccessibilityService explicitly later.

- [ ] **Step 6: Run canonical portable verification**

Run:

```bash
python -m unittest discover -s tests -q
python scripts/verify.py
git --no-pager diff --check
```

Expected: all unit tests pass, verifier prints `Verification passed.`, and diff check exits 0.

- [ ] **Step 7: Run the non-destructive Android/Termux verifier**

Run: `python scripts/verify_android.py`

Expected: platform/import/tooling checks pass and the canonical verifier passes. This does **not** count as a live autonomous Android action test.

- [ ] **Step 8: Commit documentation and final regression coverage**

```bash
git add tests/test_agent_end_to_end.py specs/AGENT_PROTOCOL.md README.md docs/ARCHITECTURE.md docs/SECURITY.md docs/ROADMAP.md
git commit -m "docs: define autonomous loop protocol and acceptance"
```

- [ ] **Step 9: Perform whole-branch verification against the implementation base**

Run:

```bash
python -m pip install -e .
python -m unittest discover -s tests -q
python scripts/verify.py --diff-range origin/main...HEAD
python scripts/verify_android.py
```

Expected: all commands exit 0. Record the exact test count and outputs before claiming completion.

## Post-implementation live acceptance gate

This gate is deliberately separate from portable CI because it requires a real configured planner and the Android device.

After the provider planner supports `mode: "agent"`, run a harmless goal inside an allowed root, for example:

```bash
lain run "create a file called hello.txt containing hello, then create a second file called done.txt containing finished"
```

Then verify:

- session is durable;
- planner returns a bounded batch;
- both actions traverse trusted policy/runtime/verification;
- state checkpoints after each action;
- a later planner turn returns explicit `complete`;
- `lain session <id> --json` shows the same verified history.

Repeat once with intentional process termination after the first verified action, then:

```bash
lain resume <session-id>
```

The second action may execute, but the first action MUST NOT execute again.

Do not describe Autonomous Loops v1 as fully hardware-validated until both live checks are observed.
