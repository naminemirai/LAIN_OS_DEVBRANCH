# Autonomous Loops v1 Design

## Summary

Autonomous Loops v1 adds a durable, resumable agent runtime above LAIN_OS's existing planner, policy, executor, verification, and audit layers.

The runtime accepts one goal and repeatedly:

```text
goal
  ↓
planner
  ↓
bounded action batch
  ↓
policy / authorization
  ↓
deterministic execution
  ↓
verification
  ↓
durable checkpoint
  ↓
re-plan from verified state
  ↺
```

The loop stops only when the planner explicitly reports `complete` or `blocked`, the user cancels the session, an authorization boundary requires user input, execution reaches an unsafe or ambiguous state, or a configured resource budget is exhausted.

This milestone does not add a background daemon, Android AccessibilityService, multi-node networking, arbitrary shell access, or self-modifying policy.

## Goals

Autonomous Loops v1 must:

- run multi-iteration goals through the existing trusted LAIN_OS execution path;
- allow each planner iteration to propose a bounded batch of actions;
- checkpoint durable session state after every action, even within a batch;
- recover from process interruption without blindly replaying completed actions;
- preserve the existing policy, confirmation, verification, audit, and idempotency boundaries;
- expose explicit planner lifecycle status: `continue`, `complete`, or `blocked`;
- enforce hard iteration, action, and wall-clock budgets;
- support explicit inspection, resume, and cancellation from the CLI;
- remain provider-independent above the existing planner adapter boundary.

## Non-goals

Autonomous Loops v1 does not implement:

- persistent background execution or Android services;
- scheduled wakeups or event-driven triggers;
- unrestricted AccessibilityService automation;
- Shizuku expansion;
- arbitrary shell or arbitrary HTTP capabilities;
- autonomous approval of confirmation-required actions;
- retries of ambiguous external writes;
- autonomous purchasing, financial transfers, or account-security changes;
- self-modifying capability policy;
- multi-node execution;
- autonomous loop nesting;
- hidden execution.

These remain later milestones.

## Existing boundaries remain authoritative

Autonomous execution is coordination, not additional authority.

The new controller sits above the existing components:

```text
AgentController
    │
    ├── PlanningService
    ├── RuntimeEngine
    ├── AgentSessionStore
    └── AgentContextBuilder
```

The following remain trusted and unchanged in authority:

- capability registry;
- argument validation;
- policy evaluation;
- confirmation requirements;
- deterministic executors;
- verification;
- append-only action audit;
- request-id duplicate protection.

The controller MUST NOT execute capabilities directly, weaken policy, manufacture confirmations, reinterpret executor failures as success, or treat planner output as verified state.

## Planner lifecycle contract

The autonomous planner response extends the current proposal shape to include a lifecycle decision:

```json
{
  "status": "continue",
  "reason": "The goal still requires work.",
  "actions": [
    {
      "type": "file.write_text",
      "arguments": {
        "path": "/example/path",
        "content": "example"
      }
    }
  ]
}
```

Allowed statuses are exactly:

- `continue`
- `complete`
- `blocked`

Rules:

- `continue` requires a non-empty action list.
- `complete` requires an empty action list.
- `blocked` requires an empty action list.
- `reason` is required, non-empty planner-supplied explanatory text.
- unknown fields fail closed.
- existing capability and argument validation remains authoritative.
- `complete` is a planner lifecycle judgment, not independent proof that an arbitrary natural-language goal is objectively satisfied.

For v1, goal completion is reported as "planner marked complete" together with the verified execution history that led to that decision. Independent goal-specific completion verification may be added later where a concrete observable postcondition exists.

## Batch semantics

Each planner iteration may return up to the configured planner action limit.

The batch is the planner's unit of intent, but execution remains sequential.

For each action in a batch:

1. persist the planned batch before the first action executes;
2. submit the action through existing policy and runtime paths;
3. execute at most once per trusted request identifier;
4. verify the result;
5. append the existing audit record;
6. persist the updated session checkpoint;
7. proceed to the next action only when the current action is in a safe success state.

If an action returns failure, denied, unsupported, confirmation-required, or verification failure, execution of the remaining batch stops immediately.

The controller then transitions the session according to the result rather than pretending the entire batch completed.

## Durable session model

Each autonomous run is represented by an `AgentSession` with a stable UUID.

Minimum durable fields:

- schema version;
- session ID;
- immutable original goal;
- lifecycle state;
- created timestamp;
- updated timestamp;
- iteration count;
- total attempted action count;
- current planner iteration;
- current planned batch;
- per-action execution state;
- verified result history;
- terminal reason when terminal;
- budget configuration;
- cumulative runtime consumed.

Session files live under:

```text
~/.lain/sessions/<session-id>/state.json
```

The storage root may later become configurable, but v1 uses this default.

State writes MUST be atomic: write a complete temporary file in the same directory, flush it, then replace the previous state file.

A corrupt or partially unreadable session file MUST fail closed and MUST NOT cause actions to be replayed.

## Session lifecycle

Minimum session states:

- `created`
- `planning`
- `executing`
- `paused_confirmation`
- `blocked`
- `complete`
- `cancelled`
- `budget_exhausted`
- `failed`

Terminal states:

- `blocked`
- `complete`
- `cancelled`
- `budget_exhausted`
- `failed`

`paused_confirmation` is resumable after explicit user confirmation through the existing authorization mechanism.

The state machine MUST reject invalid transitions.

## Recovery and replay rules

Resumption is conservative.

When `lain resume <session-id>` loads a checkpoint:

- actions recorded as successfully executed and verified are never replayed;
- actions recorded as denied, failed, unsupported, or verification-failed are not silently retried;
- confirmation-required actions remain paused until explicitly authorized;
- external writes whose outcome is ambiguous remain non-retriable under the existing external-write idempotency rule;
- a process interruption between checkpoint boundaries must not cause the controller to infer success without evidence.

If the checkpoint cannot establish whether a potentially consequential action executed, the session becomes `blocked` or `failed` rather than replaying it.

## Planner context between iterations

Every planner iteration receives enough state to reason about progress without receiving execution authority.

The context must include:

- original goal;
- current iteration number;
- configured remaining budgets;
- prior planner lifecycle decisions;
- prior proposed actions;
- normalized result status for completed actions;
- verification status and non-secret verification details;
- relevant non-secret executor result metadata;
- current capabilities from the trusted registry.

The context MUST NOT include:

- credentials;
- authorization tokens;
- recovery codes;
- hidden policy internals not needed for planning;
- unrelated audit history;
- private payloads that existing redaction rules prohibit.

Planner context is untrusted input data from the perspective of later execution.

## Resource budgets

Default v1 budgets:

```text
max_iterations = 12
max_actions_per_batch = planner_max_actions
max_total_actions = 32
max_runtime_seconds = 900
```

Rules:

- limits are enforced by the trusted controller, never by planner cooperation;
- budget counters persist in session state;
- resuming a session does not reset consumed budgets;
- reaching a budget stops further planning or execution and transitions to `budget_exhausted`;
- no configuration value may represent "unlimited" in v1.

The existing planner action bound remains separately enforced.

## Confirmation behavior

Autonomy does not imply authorization.

If the existing policy engine returns confirmation-required:

- the current batch stops;
- the session checkpoints as `paused_confirmation`;
- remaining actions in the batch do not execute;
- the controller records which trusted action requires confirmation;
- resume requires an explicit user confirmation path.

The planner cannot mark its own action confirmed and cannot convert a confirmation-required result into a retry.

## Cancellation

The CLI must support explicit cancellation:

```sh
lain cancel <session-id>
```

Cancellation:

- persists `cancelled`;
- prevents future planning and execution for that session;
- does not attempt to roll back already verified actions;
- never interrupts an executor in a way that can create an unknown external-write result unless that executor already provides a safe cancellation boundary.

In-process cancellation between actions is required in v1. Mid-action cooperative cancellation is not required unless an existing executor already supports it safely.

## CLI surface

Autonomous Loops v1 adds:

```sh
lain run "<goal>"
lain sessions
lain session <session-id>
lain resume <session-id>
lain cancel <session-id>
```

Expected behavior:

### `lain run "<goal>"`

Creates a durable session, starts iteration 1, and runs until terminal, paused, interrupted, or budget exhausted.

### `lain sessions`

Lists known local sessions with ID, goal summary, lifecycle state, iteration count, and update time.

### `lain session <session-id>`

Shows durable session state and verified progress without exposing secrets.

### `lain resume <session-id>`

Continues only a resumable non-terminal session from its last safe checkpoint.

### `lain cancel <session-id>`

Marks a resumable session cancelled.

JSON output options should follow existing CLI conventions.

## Proposed code boundaries

Create a focused `lain.agent` package:

```text
lain/agent/
    __init__.py
    models.py
    store.py
    context.py
    controller.py
```

Responsibilities:

### `models.py`

Defines immutable/session-safe domain models and lifecycle enums.

### `store.py`

Owns atomic serialization, loading, listing, and state-version validation.

### `context.py`

Builds planner-visible iteration context from trusted durable session state while excluding secrets.

### `controller.py`

Implements the bounded autonomous state machine and coordinates `PlanningService`, `RuntimeEngine`, and the session store.

Existing execution, policy, capability, verification, and audit modules remain the action authority.

## Runtime interaction

The existing `RuntimeEngine.execute()` currently accepts an entire envelope and may execute multiple actions before returning.

Autonomous Loops v1 needs per-action checkpointing inside planner batches. The implementation should therefore introduce the smallest reusable execution boundary that allows the controller to execute and receive the verified result of one trusted action at a time without duplicating policy, audit, verification, or external-write idempotency logic.

The design MUST preserve existing direct multi-action ACTION_PROTOCOL behavior.

This is an implementation constraint, not permission to move execution logic into the agent controller.

## Error handling

Planner failure before execution:

- checkpoint the failure context;
- transition to `failed` unless the error is explicitly classified as safely retryable by trusted code;
- v1 does not perform automatic provider retries.

Action failure:

- checkpoint the result;
- stop the batch;
- do not execute later batch actions;
- normally transition to `blocked` or `failed` based on trusted result classification.

Verification failure:

- execution is not considered successful;
- checkpoint the failed verification;
- do not advance to later actions.

State persistence failure:

- stop immediately;
- do not execute another action until durable state is restored;
- fail closed.

Malformed planner lifecycle output:

- fail closed as planner-output-invalid;
- execute nothing from that planner turn.

## Testing strategy

All automated tests must run without Android hardware, model APIs, or public internet access.

Required test classes:

- planner lifecycle parsing for `continue`, `complete`, and `blocked`;
- invalid lifecycle/action combinations;
- bounded multi-action batch execution;
- stop-on-first-failure behavior;
- per-action checkpoint persistence;
- process-interruption simulation between actions;
- resume without replay of completed actions;
- confirmation pause and explicit resume;
- ambiguous external-write non-retry behavior;
- cancellation;
- iteration budget exhaustion;
- total-action budget exhaustion;
- wall-clock budget exhaustion using an injected clock;
- atomic store behavior;
- corrupt state fail-closed behavior;
- invalid state-transition rejection;
- planner context redaction;
- existing direct ACTION_PROTOCOL regression coverage.

A representative integration test should prove:

```text
goal
→ planner returns two-action batch
→ action 1 succeeds and verifies
→ checkpoint
→ simulated interruption
→ resume
→ action 1 is not replayed
→ action 2 succeeds and verifies
→ next planning turn returns complete
→ session persists complete
```

## Real-device acceptance test

After the planner backend is operational on the Android device, validate a harmless multi-step goal such as:

```sh
lain run "create a file called hello.txt containing hello, then create a second file called done.txt containing finished"
```

Acceptance requires observed evidence that LAIN_OS:

1. creates a durable session;
2. obtains a bounded planner batch;
3. executes through the trusted runtime;
4. verifies each action;
5. checkpoints after each action;
6. replans after the batch;
7. receives explicit `complete`;
8. reports the terminal session state;
9. exposes the same history through `lain session <id>`.

A second hardware test should intentionally terminate the process after the first verified action and prove that `lain resume <id>` continues without replaying that action.

## Security invariants

The following are non-negotiable:

- reasoning does not imply authority;
- every action still passes trusted capability validation and policy;
- the planner cannot confirm its own actions;
- model claims are not execution evidence;
- verified completed actions are not replayed on resume;
- ambiguous external writes are not automatically retried;
- session files contain no credentials;
- session state is never treated as more authoritative than trusted audit/verification evidence where they disagree;
- autonomy is bounded by finite trusted budgets;
- cancellation and terminal states prevent further actions;
- no hidden or unrestricted execution path is introduced.

## Later milestone: persistent background agent

A later milestone may evolve this durable runtime into persistent background operation with:

- Android foreground/background service integration;
- scheduled wakeups;
- event-driven triggers;
- durable work queues;
- reboot recovery;
- explicit visible running state.

That future layer must reuse the session model rather than invent a second autonomy model.

## Exit condition

Autonomous Loops v1 is complete when a real configured planner can pursue a harmless multi-step goal across multiple planning iterations, execute bounded action batches through existing policy and verification, persist per-action checkpoints, survive an intentional process interruption without replaying already completed work, resume safely, and end in an explicit durable terminal state.
