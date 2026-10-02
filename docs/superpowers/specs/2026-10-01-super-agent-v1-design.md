# LAIN Super-Agent v1 — Goal-Driven Runtime Design

Date: 2026-10-01  
Status: Approved design, awaiting written-spec review before implementation planning.

## 1. Purpose

Evolve LAIN_OS from a bounded autonomous session loop into a persistent, goal-driven super-agent runtime.

The user supplies a goal, authority, capabilities, and resource limits. LAIN then plans, executes, verifies, persists state, replans, and continues with as few interruptions as possible until the model determines the goal is complete, policy blocks continuation, the user cancels, or a hard resource boundary is reached.

Conversation is an interface to the runtime. Conversation history is not the authoritative mission state.

## 2. Existing foundation

The repository already provides the pieces this design must extend rather than replace:

- typed ACTION_PROTOCOL requests
- policy-gated deterministic execution
- independent postcondition verification
- append-only audit records
- provider-independent planner boundaries
- durable autonomous sessions with restart/resume
- per-session budgets and checkpoints
- Android and external capability adapters
- Android GUI/runtime integration

The super-agent layer sits above those trusted primitives.

## 3. Guiding model

```text
human / durable trigger
        |
        v
event bus
        |
        v
goal manager
        |
        v
coordinator
   |      |       |
planner memory scheduler
        |
        v
subgoal DAG
   /     |      \
worker worker   worker
   \     |      /
    model router
        |
        v
skills / capability selection
        |
        v
policy engine
        |
        v
trusted executors
        |
        v
verification
        |
        v
durable state + audit
        |
        +----> coordinator replans
```

## 4. Execution philosophy

LAIN is a trusted operator, not an unrestricted model.

The model may propose plans and actions. Trusted code owns identity, policy, capability validation, authorization, execution, verification, budgets, persistence, locking, and audit.

The default runtime behavior is autonomous continuation. Failures normally trigger diagnosis, replanning, alternate approaches, backoff, and retry rather than immediate human interruption.

Unknown authority fails closed.

## 5. Top-level goal model

v1 supports one active top-level goal at a time.

A goal owns:

- immutable goal ID
- original user objective
- mutable coordinator interpretation
- status
- creation/update timestamps
- resource envelope
- authority envelope
- completion criteria/context
- current plan version
- subgoal graph
- event cursor
- memory references
- audit/session references

Suggested goal states:

```text
CREATED
RUNNING
WAITING
BLOCKED
PAUSED
CANCELLED
FAILED
COMPLETED
```

Only one top-level goal may be RUNNING at once in v1. Future versions may relax this.

## 6. Completion authority

The coordinator model decides whether the mission is complete.

Verification does not decide mission completion. Verification answers narrower factual questions such as whether an action occurred and whether its declared postcondition holds.

The coordinator therefore consumes verified state and returns a lifecycle decision such as:

```text
continue | complete | blocked
```

A `complete` decision is persisted with a final rationale and the verified evidence it relied on.

The runtime may reject malformed or internally inconsistent completion output, but it does not replace the model with a deterministic mission-completion rule.

## 7. Hierarchical planning

Planning is hierarchical.

### Coordinator responsibilities

The coordinator owns:

- mission interpretation
- decomposition
- priorities
- global resource budget
- subgoal dependency graph
- worker assignment
- conflict resolution
- mission-level replanning
- final completion decision

### Worker responsibilities

A worker receives a scoped subgoal and may:

- form a local plan
- choose among allowed tools/skills
- retry failed steps
- request additional local context
- adapt to new observations
- return structured results

A worker may not:

- rewrite the parent mission
- widen its own authority
- silently create unrelated work
- spend outside its delegated budget
- declare the parent goal complete

## 8. Generic worker runtime + specialist profiles

LAIN should not implement permanent specialist agent classes.

Use one generic worker runtime parameterized by a specialist profile:

```text
worker runtime
+ subgoal
+ model profile
+ skills
+ capabilities
+ scoped context
+ authority
+ budget
= specialist worker
```

Examples of specialist profiles include coder, researcher, reviewer, browser operator, OSINT worker, Android operator, and media worker.

Profiles are configuration and routing metadata, not separate agent architectures.

Workers are ephemeral. When their subgoal ends, they return structured output and terminate.

## 9. Dependency-aware parallelism

Subgoals form a DAG.

Each node declares at minimum:

- subgoal ID
- parent ID
- objective
- status
- dependencies
- resource claims
- worker profile
- delegated budget
- result reference

Independent READY nodes may execute concurrently.

Nodes with unmet dependencies wait.

Conflicting writes are serialized through resource claims and locks.

Initial resource-claim categories should support at least:

- repository/branch
- filesystem path or path prefix
- external account/service
- named mutable object
- arbitrary exclusive key

The coordinator resolves deadlocks or incompatible plans rather than allowing workers to race.

## 10. Scheduler states

Suggested subgoal states:

```text
PENDING
READY
RUNNING
WAITING
BLOCKED
FAILED
VERIFIED
COMPLETE
CANCELLED
```

A node becomes READY only when all required dependencies are complete and its resource claims can be acquired.

The scheduler should remain deterministic given the persisted DAG, statuses, priorities, and resource availability.

## 11. Authority model

The runtime uses a trusted-operator model.

Once a capability is enabled by policy, ordinary use should not repeatedly interrupt the user.

Low-risk and reversible operations may run automatically within the active goal's authority envelope.

Consequential operations remain subject to capability-specific policy.

Examples of operations likely to remain guarded include:

- destructive changes with broad blast radius
- credential/security changes
- privilege escalation
- financial transactions
- capability activation beyond the active authority envelope

The model never grants itself authority.

## 12. Hybrid resource envelopes

Runtime-wide defaults provide a safe ceiling. Each goal receives its own envelope.

The per-goal envelope may tighten defaults freely and may expand only where global policy allows.

Initial dimensions:

- max active runtime
- max coordinator iterations
- max worker model calls
- max total tool calls
- max estimated provider cost where available
- max parallel workers
- max repeated failures
- max identical-action retries
- max storage growth
- capability-specific limits

A resource breach transitions the affected work into BLOCKED rather than causing uncontrolled continuation.

## 13. Failure and loop handling

The normal failure loop is:

```text
failure
-> classify
-> update durable state
-> choose alternate strategy
-> retry or replan
-> verify
-> continue
```

Runtime safeguards should include:

- repeated-failure fingerprints
- cycle detection over plan/state hashes
- exponential backoff for transient failures
- bounded identical retries
- global and per-worker budgets
- cancellation checks before consequential actions
- progress checkpoints

A worker that is unable to make progress reports a structured blocker to the coordinator rather than looping indefinitely.

## 14. Durable state and memory

Structured durable state is authoritative.

The memory system is layered:

1. Goal state — mission, status, authority, budget, completion context.
2. Subgoal state — DAG nodes, dependencies, workers, attempts, outputs.
3. World state — verified facts about files, repositories, APIs, and device state.
4. Working memory — current plan and immediately relevant context.
5. Semantic memory — searchable reusable knowledge and prior outcomes.
6. Transcript archive — searchable conversation and model history.
7. Audit history — append-only action provenance.

If transcript text conflicts with verified structured state, verified structured state wins.

## 15. Context construction and compaction

Models should receive a task-specific working set rather than an ever-growing transcript.

Context assembly may draw from:

- active goal summary
- current DAG slice
- relevant verified world state
- recent execution results
- retrieved semantic memories
- scoped transcript excerpts
- applicable policy/capability metadata

The runtime periodically writes compaction checkpoints.

Compaction never deletes the original source evidence needed for audit or later retrieval.

## 16. Model routing

All reasoning models sit behind a provider-neutral model interface.

The first implementation may use one configured hosted provider by default, while the interface supports per-task model-profile requests such as:

- fast
- cheap
- deep reasoning
- coding
- vision
- large context
- private/local

A future local model backend should be an adapter behind the same router, not a separate agent runtime.

Provider credentials remain outside model-visible state and are never stored in goal memory.

## 17. Mid-mission user input

Incoming user messages become events.

The coordinator classifies each event as one of:

- informational
- goal modification
- new constraint
- priority change
- explicit interrupt
- cancel
- unrelated conversation

Normal conversation does not automatically pause the mission.

Goal modifications increment the goal state version and trigger replanning.

Explicit cancel and pause events remain trusted control-plane operations.

## 18. Crash and restart recovery

Every consequential action reaches a durable boundary before another dependent action proceeds.

Recovery sequence:

```text
restart
-> load goal + DAG
-> inspect incomplete work
-> reconcile actual world state
-> restore last verified boundary
-> resume scheduling
```

The runtime must never blindly replay an action solely because the process died before recording completion.

Existing session reconciliation behavior should be reused and generalized rather than replaced.

## 19. Capability acquisition

LAIN may discover, import, generate, or adapt new skills/capabilities while pursuing a goal.

New executable capability code follows:

```text
discover/build
-> inspect
-> validate
-> test
-> sandbox
-> register
-> policy activation
```

Acquisition and activation are separate states.

Downloaded or generated code does not become trusted execution code merely because a model requested it.

## 20. Self-modification

LAIN may modify LAIN_OS through an isolated software-delivery path.

Required shape:

```text
running system
-> isolated branch/worktree
-> implementation
-> tests
-> verification/review
-> controlled promotion
```

The running production instance must not casually mutate the exact code it is executing.

v1 may expose the workflow and state model before full automated promotion is implemented.

## 21. External side effects and provenance

Authorized external actions may run autonomously within policy.

Every consequential action must be attributable to:

- goal ID
- subgoal ID
- worker ID
- plan version
- capability
- redacted arguments
- policy decision
- execution result
- verification result
- timestamp

This provenance should be queryable from the operator UI and durable audit records.

## 22. Durable triggers

LAIN may start or resume work without a fresh chat message only from an explicitly authorized durable trigger.

Initial trigger types:

- schedule
- webhook
- state-change event
- monitored condition
- standing goal

Triggers create control-plane events. They do not bypass normal policy, budgets, or goal arbitration.

The system must not invent new missions merely because a model believes work would be useful.

## 23. Operator interface

The UI combines two layers.

### Conversational layer

Primary interaction is chat and later voice.

Users can create, modify, pause, resume, inspect, and cancel goals in ordinary language.

### Operator console

An expandable developer view exposes:

- goal state
- current coordinator decision
- DAG and node statuses
- workers
- model/provider usage
- tool calls
- resource locks
- budgets
- memory references
- checkpoints
- policy decisions
- audit history
- blockers and failures

The GUI should optimize for calm observability rather than constant approval prompts.

## 24. Integration with the current agent controller

The existing durable session loop is the migration base.

Implementation should proceed by extraction and generalization:

1. Treat the current session as the first single-worker goal execution primitive.
2. Separate coordinator lifecycle from one-shot/batch planning details.
3. Introduce explicit Goal and Subgoal models without breaking current session persistence.
4. Add DAG scheduling while retaining sequential execution as the degenerate one-node case.
5. Wrap the current planner behind the future model-router interface.
6. Reuse the existing trusted execution, policy, verification, audit, and reconciliation paths unchanged wherever possible.
7. Add worker scoping only after the coordinator and DAG are stable.
8. Add parallel execution only after deterministic resource claims/locking are tested.

Backward-compatible CLI behavior should remain available throughout the migration.

## 25. Proposed v1 module boundaries

Suggested new or expanded modules:

```text
lain/
  goals/
    models.py
    store.py
    manager.py
    events.py
  coordinator/
    controller.py
    planning.py
    completion.py
  workers/
    runtime.py
    models.py
    profiles.py
  scheduling/
    dag.py
    scheduler.py
    locks.py
  memory/
    working.py
    semantic.py
    context.py
  models/
    router.py
    profiles.py
    provider.py
  triggers/
    models.py
    dispatcher.py
```

Existing `lain/agent` code may migrate incrementally into these boundaries. No wholesale rewrite is required.

## 26. v1 implementation boundary

The first super-agent implementation should prove:

- one durable top-level goal
- hierarchical coordinator/worker boundary
- persisted subgoal DAG
- dependency-aware scheduling
- deterministic resource locking
- generic workers with specialist profiles
- structured event handling
- restart/reconciliation
- hybrid budgets
- provider-neutral model routing interface
- operator-visible state
- model-owned mission completion backed by verified facts

v1 does not require:

- unrestricted background Android control
- multiple simultaneous top-level goals
- arbitrary self-installing executable code
- automatic production self-upgrade
- fully local inference
- unconstrained worker swarms
- hidden or unaudited side effects

## 27. Testing strategy

Required test layers:

### Model tests

- strict Goal/Subgoal/Event serialization
- state transition validation
- budget accounting
- worker scope inheritance
- completion decision parsing

### DAG tests

- dependency ordering
- independent-node readiness
- cycle rejection
- deterministic scheduling
- cancellation propagation

### Lock tests

- conflicting resource claims serialize
- non-conflicting work may proceed
- locks release on success/failure/recovery
- stale lock recovery is safe

### Recovery tests

- crash before execution
- crash during action
- execution complete but checkpoint behind
- checkpoint complete but worker lost
- restart with blocked/paused work

### Policy tests

- worker cannot widen authority
- goal override cannot exceed global policy
- new capability activation stays policy-gated
- external actions preserve provenance

### Context tests

- verified structured state overrides transcript conflict
- context retrieval is scoped
- compaction preserves references to original evidence

### Integration tests

- one goal -> coordinator -> subgoals -> workers -> verified completion
- independent subgoals execute concurrently only when safe
- mid-mission user event triggers replanning without automatic cancellation
- provider adapter can be swapped without changing coordinator logic

## 28. Acceptance criteria

The first implementation milestone is complete when all of the following are true:

- a goal survives process restart
- the coordinator can decompose a goal into persisted subgoals
- the scheduler executes dependency-safe work
- resource conflicts cannot race
- workers receive scoped context/authority/budgets
- worker results merge into authoritative goal state
- coordinator replans from verified results
- failures do not immediately require human input
- user events can modify or cancel an active goal
- the coordinator may mark the mission complete
- audit records connect every action to goal/subgoal/worker provenance
- existing ACTION_PROTOCOL execution and policy tests remain green
- existing `lain run` behavior remains supported or has a documented compatibility migration

## 29. Design invariants

1. The model reasons; trusted code controls side effects.
2. Durable state outranks transcript history.
3. Workers are scoped and disposable.
4. The coordinator owns the mission.
5. Verification establishes facts; the coordinator decides completion.
6. Authority is explicit and cannot be self-expanded.
7. Parallelism is dependency- and conflict-aware.
8. Recovery reconciles reality before retrying.
9. Autonomy ends at configured policy/resource boundaries.
10. Every consequential action leaves provenance.

## 30. Next stage

After this written spec is reviewed, the next step is a detailed implementation plan that maps these boundaries onto the existing `lain/agent`, `lain/planning`, `lain/runtime`, Android UI, and test structure in small reviewable increments.
