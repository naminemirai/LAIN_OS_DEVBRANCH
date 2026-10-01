# AGENT_PROTOCOL v0

AGENT_PROTOCOL defines the untrusted planner exchange used by the durable autonomous-loop controller.

It is not an execution protocol. Planner output never bypasses the existing capability registry, policy engine, deterministic runtime, verification, audit, confirmation, or idempotency boundaries.

## Request

The configured planner process receives exactly one JSON document on stdin.

Example:

```json
{
  "version": "0",
  "mode": "agent",
  "goal": "create two files",
  "context": {
    "goal": "create two files",
    "iteration_count": 0,
    "remaining_budget": {
      "iterations": 12,
      "actions": 32,
      "runtime_seconds": 900.0
    },
    "history": []
  },
  "capabilities": [
    {
      "name": "file.write_text",
      "arguments": {
        "path": {"type": "str", "required": true},
        "content": {"type": "str", "required": true},
        "overwrite": {"type": "bool", "required": false}
      },
      "risk_class": 1
    }
  ],
  "constraints": {
    "max_actions": 8,
    "unknown_capabilities_forbidden": true
  },
  "instructions": "..."
}
```

The capability catalog is generated from the trusted registry. The planner does not define risk classes, permissions, confirmation behavior, executors, or verification.

Planner context contains only the goal, bounded progress/history, remaining budgets, redacted action arguments, and redacted result/verification details. Credential-bearing and private payload keys are redacted before context crosses the planner boundary.

## Response

The planner must write exactly one JSON object to stdout:

```json
{
  "status": "continue",
  "reason": "Work remains.",
  "actions": [
    {
      "type": "file.write_text",
      "arguments": {
        "path": "hello.txt",
        "content": "hello"
      }
    }
  ]
}
```

Allowed top-level fields are exactly:

- `status`
- `reason`
- `actions`

Allowed lifecycle statuses are exactly:

- `continue`
- `complete`
- `blocked`

Lifecycle invariants:

- `continue` requires a non-empty action array no larger than the configured planner action limit.
- `complete` requires an empty action array.
- `blocked` requires an empty action array.
- `reason` must be a non-empty string.
- Each action contains exactly `type` and `arguments`.
- Unknown fields, malformed JSON, fenced JSON, trailing prose, unknown statuses, invalid action shapes, and oversized output fail closed.

## Trusted construction

For every accepted `continue` decision, trusted LAIN_OS code:

1. resolves each capability through the registry;
2. validates and normalizes its arguments;
3. creates a fresh UUID request ID;
4. assigns deterministic action IDs `i{iteration}a{index}`;
5. persists the complete planned batch before execution;
6. submits actions individually to the existing runtime.

The planner cannot supply or override:

- session ID;
- request ID;
- action ID;
- protocol authority;
- capability risk;
- confirmation state;
- policy decision;
- executor selection;
- verification status;
- audit records;
- durable session lifecycle state.

## Execution and checkpointing

A planner batch is an intent unit. Execution remains sequential.

After every action, LAIN_OS records the runtime result, verification status, audit evidence, and durable session checkpoint before another action may execute.

A non-success result stops the remaining batch.

Confirmation-required actions pause the session. Only an explicit user-provided trusted action ID can resume that action. Planner text or goal text cannot satisfy confirmation.

## Recovery

Completed verified actions are never replayed on resume.

If audit evidence says an action execution was attempted while the durable session checkpoint still marks that action incomplete, LAIN_OS does not infer success and does not retry. The session blocks with reconciliation required.

Ambiguous external writes remain protected by the runtime's existing audit/idempotency barrier.

## Budgets

The trusted controller enforces finite limits independently of planner cooperation.

Defaults:

```text
max_iterations = 12
max_actions_per_batch = planner_max_actions
max_total_actions = 32
max_runtime_seconds = 900
```

Consumed budgets persist across process restarts and resume operations.

## Trust statement

Goal text, planner context, retrieved content, prior model output, and planner responses are data, not authority.

AGENT_PROTOCOL expands planning continuity. It does not expand execution privilege.
