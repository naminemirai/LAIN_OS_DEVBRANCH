# LAIN Super-Agent Core v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the persistent goal/coordinator/DAG/worker runtime that turns the existing durable `lain run` loop into the trusted execution primitive beneath a goal-driven super-agent.

**Architecture:** Add a new goal layer beside the current `lain.agent` session layer. The coordinator owns a durable top-level goal and dependency graph; generic workers reuse the existing `AgentController`, `RuntimeEngine`, policy, verification, audit, and reconciliation paths. Model routing stays provider-neutral by routing both coordinator and worker planners through named profiles, with the current subprocess/Groq planner as the first provider.

**Tech Stack:** Python 3.11+ standard library, dataclasses/enums/JSON/`pathlib`/`fcntl`/`concurrent.futures`, existing LAIN action runtime and planner adapters, `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-01-super-agent-v1-design.md`

## Global Constraints

- Python remains `>=3.11`; add no runtime third-party Python dependency.
- Preserve ACTION_PROTOCOL validation, policy, deterministic execution, verification, audit redaction, and duplicate-execution protections.
- Model output is untrusted input; trusted code assigns goal IDs, subgoal IDs, worker session IDs, action IDs, request IDs, authority, locks, budgets, and execution state.
- Exactly one top-level goal may be `RUNNING` at a time in v1.
- Verification establishes action/world facts; the coordinator model owns the final mission `complete | blocked | continue` decision.
- Worker authority is narrower than or equal to goal/global authority and must be enforced again at the trusted runtime boundary, not only hidden from model context.
- Existing `lain run`, `sessions`, `session`, `resume`, and `cancel` behavior stays supported while the new goal path is introduced.
- Goal/session state directories remain private (`0700`) and state files remain `0600`, written atomically with `fsync` + replace.
- Planner/provider/executor credentials never enter model-visible goal state, worker context, memory, CLI JSON, or audit records.
- Never use `shell=True`; preserve fixed-argv subprocess boundaries and bounded stdout/stderr.
- Android integration is a separate dependent plan; this core plan must remain portable on ordinary Linux/Termux.
- No unrestricted background daemon, AccessibilityService, automatic production self-upgrade, or arbitrary downloaded-code activation is introduced by this plan.

## Review Focus

- Malformed or cyclic subgoal dependencies must fail before any worker starts; Task 2 adds rejection tests for unknown/self/cyclic dependencies.
- Conflicting resource claims must serialize while independent claims may run together; Tasks 2 and 7 add deterministic lock/scheduler concurrency tests.
- A crash where worker execution is ahead of the goal checkpoint must reconcile from durable worker/audit state and never replay a completed action; Task 6 adds recovery acceptance tests.
- A compromised/malformed worker planner must not execute a capability outside the worker profile even if it constructs a valid ACTION_PROTOCOL envelope; Task 4 tests trusted scope enforcement.
- A coordinator `complete` decision while nonterminal subgoals remain must fail closed as an inconsistent lifecycle decision rather than silently abandoning work; Task 6 pins this rule.

---

### Task 1: Durable Goal, Subgoal, Budget, and Store Models

**Files:**
- Create: `lain/goals/__init__.py`
- Create: `lain/goals/models.py`
- Create: `lain/goals/store.py`
- Create: `tests/test_goal_models.py`
- Create: `tests/test_goal_store.py`

**Interfaces:**
- Consumes: existing `lain.agent.models.AgentBudget` only for delegated worker budgets; goal budgeting is separate.
- Produces:
  - `GoalStatus`
  - `SubgoalStatus`
  - `ResourceEnvelope`
  - `ResourceClaim`
  - `FailureCount`
  - `SubgoalState`
  - `GoalState`
  - `GoalStore`

Use these exact public shapes:

```python
class GoalStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"

class SubgoalStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    FAILED = "failed"
    VERIFIED = "verified"
    COMPLETE = "complete"
    CANCELLED = "cancelled"

@dataclass(frozen=True, slots=True)
class ResourceEnvelope:
    max_coordinator_iterations: int = 32
    max_total_actions: int = 128
    max_runtime_seconds: float = 3600.0
    max_parallel_workers: int = 4
    max_repeated_failures: int = 3

@dataclass(frozen=True, slots=True)
class ResourceClaim:
    kind: str
    key: str

@dataclass(frozen=True, slots=True)
class FailureCount:
    fingerprint: str
    count: int

@dataclass(frozen=True, slots=True)
class SubgoalState:
    subgoal_id: str
    parent_id: str | None
    objective: str
    status: SubgoalStatus
    dependencies: tuple[str, ...]
    resource_claims: tuple[ResourceClaim, ...]
    worker_profile: str
    worker_session_id: str | None
    result: dict[str, Any] | None
    failure_fingerprint: str | None

@dataclass(frozen=True, slots=True)
class GoalState:
    version: str
    goal_id: str
    objective: str
    status: GoalStatus
    created_at: str
    updated_at: str
    plan_version: int
    subgoals: tuple[SubgoalState, ...]
    budget: ResourceEnvelope
    coordinator_iterations: int
    total_attempted_actions: int
    cumulative_runtime_seconds: float
    failure_counts: tuple[FailureCount, ...]
    recent_plan_hashes: tuple[str, ...]
    last_event_seq: int
    terminal_reason: str | None
```

`GoalState.version` is `"1"`. UUID-bearing IDs use canonical UUID text.

`GoalStore(root: Path)` mirrors `AgentSessionStore` with:
- `path_for(goal_id: str) -> Path`
- `save(goal: GoalState) -> None`
- `load(goal_id: str) -> GoalState`
- `list_goals() -> tuple[GoalState, ...]`
- `lease(goal_id: str) -> Iterator[None]`

- [ ] **Step 1: Write failing model round-trip and validation tests**

```python
def test_goal_round_trip_preserves_nested_subgoals():
    goal = sample_goal()
    assert GoalState.from_dict(goal.to_dict()) == goal

def test_goal_rejects_duplicate_subgoal_ids_and_noncanonical_ids():
    with self.assertRaises(LainError):
        GoalState.from_dict(invalid_duplicate_ids)

def test_resource_envelope_rejects_bool_zero_negative_and_nonfinite_values():
    for raw in invalid_envelopes:
        with self.assertRaises(LainError):
            ResourceEnvelope.from_dict(raw)
```

- [ ] **Step 2: Run model tests and verify red**

Run: `python -m unittest tests.test_goal_models -v`  
Expected: FAIL because `lain.goals` does not exist.

- [ ] **Step 3: Implement the exact models and strict `to_dict` / `from_dict` parsing**

Use the same fail-closed parsing style as `lain/agent/models.py`; unknown fields are errors. `SubgoalState.result` must be either `None` or a JSON-object-shaped `dict`.

- [ ] **Step 4: Run model tests and verify green**

Run: `python -m unittest tests.test_goal_models -v`  
Expected: PASS.

- [ ] **Step 5: Write failing atomic/private store tests**

```python
def test_goal_store_save_load_list_and_permissions():
    store.save(goal)
    assert store.load(goal.goal_id) == goal
    assert stat.S_IMODE(store.path_for(goal.goal_id).stat().st_mode) == 0o600

def test_goal_store_lease_is_exclusive():
    with store.lease(goal.goal_id):
        with self.assertRaises(LainError):
            with store.lease(goal.goal_id):
                pass
```

Also port the existing replace-failure test from `tests/test_agent_store.py`.

- [ ] **Step 6: Run store tests and verify red**

Run: `python -m unittest tests.test_goal_store -v`  
Expected: FAIL because `GoalStore` is not implemented.

- [ ] **Step 7: Implement `GoalStore` using the `AgentSessionStore` atomic-write/lease pattern**

Do not share lock files between unrelated goal IDs. Keep `state.json` and goal directories private.

- [ ] **Step 8: Run Task 1 tests**

Run: `python -m unittest tests.test_goal_models tests.test_goal_store -v`  
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add lain/goals tests/test_goal_models.py tests/test_goal_store.py
git commit -m "feat: add durable super-agent goal state"
```

---

### Task 2: Dependency Graph Validation, Readiness, and Resource Claims

**Files:**
- Create: `lain/scheduling/__init__.py`
- Create: `lain/scheduling/dag.py`
- Create: `lain/scheduling/locks.py`
- Create: `tests/test_goal_dag.py`
- Create: `tests/test_resource_locks.py`

**Interfaces:**
- Consumes: `SubgoalState`, `SubgoalStatus`, `ResourceClaim`.
- Produces:

```python
def validate_subgoal_graph(subgoals: tuple[SubgoalState, ...]) -> None
def ready_subgoal_ids(subgoals: tuple[SubgoalState, ...]) -> tuple[str, ...]

class ResourceLockTable:
    def __init__(self, subgoals: tuple[SubgoalState, ...]): ...
    def can_acquire(self, subgoal: SubgoalState) -> bool: ...
    def acquire(self, subgoal: SubgoalState) -> "ResourceLockTable": ...
    def release(self, subgoal_id: str) -> "ResourceLockTable": ...
```

A claim conflicts only when both `kind` and `key` match exactly in v1. Path-prefix expansion belongs to the caller that constructs a claim, not the lock table.

`ready_subgoal_ids` returns IDs in persisted tuple order for deterministic scheduling. A node is ready when status is `PENDING` or `READY`, every dependency is `COMPLETE` or `VERIFIED`, and the graph itself is valid.

- [ ] **Step 1: Write failing DAG tests**

```python
def test_independent_nodes_are_ready_in_persisted_order():
    assert ready_subgoal_ids((a, b)) == (a.subgoal_id, b.subgoal_id)

def test_dependency_waits_until_parent_complete():
    assert ready_subgoal_ids((pending_parent, child)) == (pending_parent.subgoal_id,)

def test_unknown_self_and_cycles_fail_closed():
    for graph in bad_graphs:
        with self.assertRaises(LainError):
            validate_subgoal_graph(graph)
```

- [ ] **Step 2: Run DAG tests and verify red**

Run: `python -m unittest tests.test_goal_dag -v`  
Expected: FAIL.

- [ ] **Step 3: Implement graph validation and deterministic readiness**

Use DFS or Kahn validation; raise `AGENT_STATE_INVALID` until a goal-specific error code is added.

- [ ] **Step 4: Write failing lock tests**

```python
def test_same_claim_conflicts():
    table = ResourceLockTable((running_repo_a,))
    self.assertFalse(table.can_acquire(ready_repo_a))

def test_independent_claims_do_not_conflict():
    table = ResourceLockTable((running_repo_a,))
    self.assertTrue(table.can_acquire(ready_repo_b))
```

Also test release and reconstruction from persisted `RUNNING` nodes.

- [ ] **Step 5: Implement immutable `ResourceLockTable`**

Treat every `RUNNING` subgoal's claims as already held when reconstructing after restart.

- [ ] **Step 6: Run Task 2 tests**

Run: `python -m unittest tests.test_goal_dag tests.test_resource_locks -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lain/scheduling tests/test_goal_dag.py tests/test_resource_locks.py
git commit -m "feat: add dependency-aware goal scheduling"
```

---

### Task 3: Provider-Neutral Model Router and Coordinator Planner Contract

**Files:**
- Create: `lain/models/__init__.py`
- Create: `lain/models/router.py`
- Create: `lain/coordinator/__init__.py`
- Create: `lain/coordinator/models.py`
- Create: `lain/coordinator/planning.py`
- Modify: `lain/planning/adapter.py`
- Modify: `lain/planning/protocol.py`
- Modify: `lain/planner_adapters/groq.py`
- Modify: `lain/config.py`
- Test: `tests/test_model_router.py`
- Test: `tests/test_coordinator_planner.py`
- Test: `tests/test_groq_planner.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: current `SubprocessPlanner`, `PlannerConfig`, goal context dictionaries.
- Produces:

```python
@dataclass(frozen=True, slots=True)
class ModelProfile:
    name: str

class ModelRouter:
    def __init__(self, planners: Mapping[str, object], default_profile: str = "default"): ...
    def agent(self, profile: str | None = None) -> AgentPlanner: ...
    def coordinator(self, profile: str | None = None) -> CoordinatorPlanner: ...

class CoordinatorStatus(str, Enum):
    CONTINUE = "continue"
    COMPLETE = "complete"
    BLOCKED = "blocked"

@dataclass(frozen=True, slots=True)
class ProposedResourceClaim:
    kind: str
    key: str

@dataclass(frozen=True, slots=True)
class ProposedSubgoal:
    key: str
    objective: str
    depends_on: tuple[str, ...]
    worker_profile: str
    resource_claims: tuple[ProposedResourceClaim, ...]

@dataclass(frozen=True, slots=True)
class CoordinatorDecision:
    status: CoordinatorStatus
    reason: str
    subgoals: tuple[ProposedSubgoal, ...]

class CoordinatorPlanner(Protocol):
    def coordinate(
        self,
        goal: str,
        context: dict[str, Any],
        worker_profiles: tuple[str, ...],
    ) -> CoordinatorDecision: ...
```

Extend `SubprocessPlanner` with `coordinate(...) -> CoordinatorDecision`.

Add to `AgentConfig`:
- `max_subgoals_per_plan: int = 8`

Config key:
- `agent_max_subgoals_per_plan`

Coordinator subprocess request is exact JSON:

```json
{
  "version": "0",
  "mode": "coordinator",
  "goal": "...",
  "context": {},
  "worker_profiles": ["default", "coder"],
  "constraints": {"max_subgoals": 8},
  "instructions": "..."
}
```

Coordinator model output is exact JSON:

```json
{
  "status": "continue|complete|blocked",
  "reason": "...",
  "subgoals": [{
    "key": "local-name",
    "objective": "...",
    "depends_on": [],
    "worker_profile": "default",
    "resource_claims": [{"kind": "filesystem", "key": "workspace"}]
  }]
}
```

`complete` and `blocked` require zero proposed subgoals. `continue` may contain zero proposals only when the supplied context already has nonterminal work; `CoordinatorPlanningService` enforces that condition, not the raw parser.

- [ ] **Step 1: Write failing model-router tests**

```python
def test_router_returns_named_and_default_planners():
    self.assertIs(router.agent(), default_planner)
    self.assertIs(router.coordinator("deep"), deep_planner)

def test_unknown_profile_fails_closed():
    with self.assertRaises(LainError):
        router.agent("missing")
```

- [ ] **Step 2: Implement `ModelRouter`**

The router stores objects; interface validation happens when `agent()` / `coordinator()` is requested via `hasattr` for `decide` / `coordinate`.

- [ ] **Step 3: Write failing coordinator protocol/parser tests**

Pin exact fields, strict unknown-field rejection, bounded subgoal count, nonempty keys/objectives/profile names, and strict resource-claim objects.

- [ ] **Step 4: Extend `lain/planning/protocol.py` and `SubprocessPlanner.coordinate`**

Add:
- `coordinator_planner_request(...)`
- `parse_coordinator_decision(...)`

Reuse `_decode_json`; do not reuse action parsing.

- [ ] **Step 5: Run coordinator protocol tests**

Run: `python -m unittest tests.test_model_router tests.test_coordinator_planner -v`  
Expected: PASS.

- [ ] **Step 6: Add failing Groq coordinator contract tests**

Pin:
- exact request acceptance for `mode == "coordinator"`
- strict response schema
- invalid profile/claim shapes rejected
- model output cannot add authority/confirmation/executor fields
- existing one-shot and agent schemas unchanged

- [ ] **Step 7: Extend `groq.py` for coordinator mode**

Add `_is_coordinator_request`. Build a separate strict JSON schema for coordinator subgoals. Keep the same security system instruction and credential handling.

- [ ] **Step 8: Add/configure `agent_max_subgoals_per_plan`**

Update `AgentConfig`, `_ALLOWED_CONFIG_KEYS`, TOML loader, and config tests. Default: `8`.

- [ ] **Step 9: Run planner/config regression set**

Run:

```bash
python -m unittest \
  tests.test_model_router \
  tests.test_coordinator_planner \
  tests.test_agent_planner \
  tests.test_planner \
  tests.test_groq_planner \
  tests.test_config -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add lain/models lain/coordinator lain/planning lain/planner_adapters/groq.py lain/config.py tests
git commit -m "feat: add coordinator model routing contract"
```

---

### Task 4: Generic Worker Profiles and Trusted Capability Scope

**Files:**
- Create: `lain/workers/__init__.py`
- Create: `lain/workers/models.py`
- Create: `lain/workers/profiles.py`
- Create: `lain/workers/runtime.py`
- Create: `tests/test_worker_profiles.py`
- Create: `tests/test_worker_runtime.py`

**Interfaces:**
- Consumes:
  - `AgentController`
  - `AgentPlanningService`
  - `AgentSessionStore`
  - `RuntimeEngine`
  - `ModelRouter.agent(profile)`
- Produces:

```python
@dataclass(frozen=True, slots=True)
class WorkerProfile:
    name: str
    model_profile: str
    capability_names: tuple[str, ...]
    budget: AgentBudget

class WorkerProfileRegistry:
    def get(self, name: str) -> WorkerProfile: ...
    def names(self) -> tuple[str, ...]: ...

@dataclass(frozen=True, slots=True)
class WorkerResult:
    session_id: str
    status: AgentSessionStatus
    terminal_reason: str | None
    attempted_actions: int
    verified_successes: int

class ScopedRuntime:
    def __init__(
        self,
        runtime: RuntimeEngine,
        allowed_capabilities: frozenset[str],
        provenance: Mapping[str, str],
    ): ...
    def execute_action(
        self,
        envelope: ActionEnvelope,
        action_id: str,
        *,
        confirmed_action_ids: frozenset[str] = frozenset(),
    ) -> ActionResult: ...

class WorkerRuntime:
    def start(self, goal_id: str, subgoal: SubgoalState, profile: WorkerProfile) -> str: ...
    def run(self, session_id: str) -> WorkerResult: ...
    def resume(self, session_id: str) -> WorkerResult: ...
    def inspect(self, session_id: str) -> WorkerResult: ...
```

`WorkerRuntime` creates one durable `AgentSession` per subgoal and stores its ID in the parent subgoal. The existing `AgentController` remains the worker execution engine.

`ScopedRuntime` checks `record.action.type` against `allowed_capabilities` before delegating to `RuntimeEngine`, even if an injected/malformed planner somehow bypasses the restricted capability catalog.

- [ ] **Step 1: Write failing profile-registry tests**

Cover duplicate names, unknown profiles, unknown capability names, and model-profile lookup.

- [ ] **Step 2: Implement profile models/registry**

Provide one built-in `"default"` profile whose capability list is `DEFAULT_REGISTRY.names()` and whose model profile is `"default"`. Tests may define narrower profiles.

- [ ] **Step 3: Write failing trusted-scope tests**

```python
def test_worker_cannot_execute_capability_outside_profile_even_with_valid_envelope():
    scoped = ScopedRuntime(runtime, frozenset({"file.write_text"}), provenance)
    with self.assertRaises(LainError):
        scoped.execute_action(open_uri_envelope, "a1")
```

Assert no audit execution attempt and no external effect.

- [ ] **Step 4: Implement `ScopedRuntime`**

Reject out-of-scope capability with `POLICY_DENIED`. Do not mutate the envelope.

- [ ] **Step 5: Write failing worker-lifecycle tests**

Use a fake model router and real `RuntimeEngine` to prove:
- start creates a durable agent session
- run completes and writes a file
- inspect summarizes existing session state
- a blocked/failed worker returns structured `WorkerResult`

- [ ] **Step 6: Implement `WorkerRuntime` as a factory around existing agent components**

Each worker gets:
- planner from `ModelRouter.agent(profile.model_profile)`
- `AgentPlanningService` with a registry filtered to `profile.capability_names`
- `ScopedRuntime`
- shared `AgentSessionStore`
- the profile's `AgentBudget`

Do not copy `AgentController` logic.

- [ ] **Step 7: Run worker tests**

Run: `python -m unittest tests.test_worker_profiles tests.test_worker_runtime tests.test_agent_end_to_end -v`  
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add lain/workers tests/test_worker_profiles.py tests/test_worker_runtime.py
git commit -m "feat: add scoped generic worker runtime"
```

---

### Task 5: Goal Events, Searchable Memory, and Coordinator Context

**Files:**
- Create: `lain/goals/events.py`
- Create: `lain/memory/__init__.py`
- Create: `lain/memory/store.py`
- Create: `lain/memory/context.py`
- Create: `tests/test_goal_events.py`
- Create: `tests/test_memory_store.py`
- Create: `tests/test_goal_context.py`

**Interfaces:**
- Consumes: `GoalState`, `SubgoalState`, worker result summaries, existing audit redaction helpers.
- Produces:

```python
class GoalEventKind(str, Enum):
    USER_INPUT = "user_input"
    INFORMATIONAL = "informational"
    GOAL_MODIFICATION = "goal_modification"
    NEW_CONSTRAINT = "new_constraint"
    PRIORITY_CHANGE = "priority_change"
    INTERRUPT = "interrupt"
    CANCEL = "cancel"
    UNRELATED = "unrelated"

@dataclass(frozen=True, slots=True)
class GoalEvent:
    seq: int
    event_id: str
    kind: GoalEventKind
    content: str
    created_at: str

class GoalEventStore:
    def append(self, goal_id: str, kind: GoalEventKind, content: str) -> GoalEvent: ...
    def after(self, goal_id: str, seq: int) -> tuple[GoalEvent, ...]: ...

@dataclass(frozen=True, slots=True)
class MemoryRecord:
    memory_id: str
    namespace: str
    text: str
    metadata: dict[str, Any]
    created_at: str

class LocalMemoryStore:
    def append(self, record: MemoryRecord) -> None: ...
    def search(self, query: str, *, namespace: str | None = None, limit: int = 8) -> tuple[MemoryRecord, ...]: ...

def build_goal_context(
    goal: GoalState,
    *,
    events: tuple[GoalEvent, ...],
    memories: tuple[MemoryRecord, ...],
    worker_sessions: Mapping[str, AgentSession],
) -> dict[str, Any]
```

`GoalEventStore` is append-only JSONL under `<goal-dir>/events.jsonl` and uses exclusive file locking.

`LocalMemoryStore` is an initial standard-library retrieval backend: case-folded token overlap with deterministic tie-breaking by newest record. The interface, not this algorithm, is authoritative; an embedding-backed store can replace it later.

`build_goal_context` returns structured state with redacted worker action details. It does not dump full transcripts.

- [ ] **Step 1: Write failing event-store sequence and durability tests**

Pin monotonic per-goal `seq`, UUID event IDs, private file permissions, invalid/corrupt line handling, and concurrent append serialization.

- [ ] **Step 2: Implement `GoalEventStore`**

Append one complete JSON line under `flock`; `after()` ignores malformed lines but never renumbers valid events.

- [ ] **Step 3: Write failing memory search tests**

```python
def test_search_prefers_more_token_overlap_then_newer():
    self.assertEqual(store.search("android battery", limit=2), (battery_android, battery_note))

def test_namespace_filter_is_strict():
    self.assertEqual(store.search("build", namespace="project:a"), (project_a_record,))
```

- [ ] **Step 4: Implement `LocalMemoryStore`**

Keep original records retrievable; no compaction deletes source text.

- [ ] **Step 5: Write failing context/redaction tests**

Pin:
- current goal objective/status/budget
- DAG statuses/dependencies
- only events after `last_event_seq`
- retrieved memory metadata/text
- worker summaries
- private action payloads redacted
- verified structured state present even if an event claims contradictory success

- [ ] **Step 6: Implement `build_goal_context`**

Use `redact` and `redact_android_narratives` before returning model-visible context.

- [ ] **Step 7: Run Task 5 tests**

Run: `python -m unittest tests.test_goal_events tests.test_memory_store tests.test_goal_context -v`  
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add lain/goals/events.py lain/memory tests/test_goal_events.py tests/test_memory_store.py tests/test_goal_context.py
git commit -m "feat: add goal events and scoped memory context"
```

---

### Task 6: Sequential Coordinator Control Loop and Crash Reconciliation

**Files:**
- Create: `lain/coordinator/controller.py`
- Create: `tests/test_coordinator_controller.py`
- Create: `tests/test_super_agent_end_to_end.py`
- Modify: `lain/coordinator/planning.py`
- Modify: `lain/goals/models.py` only if helper transition methods are needed; do not change persisted field names from Task 1.

**Interfaces:**
- Consumes:
  - `GoalStore`
  - `GoalEventStore`
  - `LocalMemoryStore`
  - `ModelRouter.coordinator(...)`
  - `CoordinatorPlanningService`
  - `WorkerRuntime`
  - DAG/lock helpers
  - `build_goal_context`
- Produces:

```python
class GoalCoordinator:
    def create(
        self,
        objective: str,
        *,
        budget: ResourceEnvelope | None = None,
    ) -> GoalState: ...

    def step(self, goal_id: str) -> GoalState: ...
    def run_until_stop(self, goal_id: str) -> GoalState: ...
    def cancel(self, goal_id: str) -> GoalState: ...
    def post_event(self, goal_id: str, kind: GoalEventKind, content: str) -> GoalEvent: ...
```

`run_until_stop` is foreground/on-demand. It returns when the goal reaches `COMPLETED`, `BLOCKED`, `PAUSED`, `CANCELLED`, or `FAILED`.

Sequential-first state machine:

1. Lease and load goal.
2. Apply trusted `CANCEL` / `INTERRUPT` events.
3. Reconcile persisted `RUNNING` subgoals against their durable worker sessions before any replay.
4. If a dependency-safe subgoal is ready, acquire its claims, create/resume one worker, run it, persist result, release claims.
5. If work remains, loop.
6. When no runnable work remains, call coordinator planner with structured context.
7. Materialize proposed subgoals with trusted UUIDs, resolve proposal-local dependency keys, validate DAG, increment `plan_version`, persist.
8. On `complete`, require no nonterminal subgoals; then persist `COMPLETED` with the model reason.
9. On `blocked`, persist `BLOCKED`.
10. Never let the coordinator model directly execute ACTION_PROTOCOL actions.

- [ ] **Step 1: Write failing create/plan/materialize tests**

Pin one active top-level goal: creating a second while another is `RUNNING` raises `AGENT_STATE_INVALID`.

Pin local proposal keys are mapped to trusted UUID subgoal IDs and dependency references are rewritten.

- [ ] **Step 2: Implement `GoalCoordinator.create` and planning materialization**

`CREATED` transitions to `RUNNING` on the first `step`.

- [ ] **Step 3: Write failing sequential worker tests**

Prove a two-node dependency graph runs parent then child and persists each worker session ID/result.

- [ ] **Step 4: Implement sequential scheduling and worker result mapping**

Map worker session statuses:
- `COMPLETE` -> subgoal `COMPLETE`
- `BLOCKED` -> subgoal `BLOCKED`
- `FAILED` / `BUDGET_EXHAUSTED` -> subgoal `FAILED`
- `PAUSED_CONFIRMATION` -> subgoal `WAITING`

- [ ] **Step 5: Add failing model-owned completion consistency tests**

```python
def test_complete_with_nonterminal_subgoal_fails_closed():
    coordinator_planner.returns(complete("done"))
    with self.assertRaises(LainError):
        coordinator.step(goal_id)
```

Also prove `complete` succeeds after all relevant subgoals are terminal and its reason becomes `terminal_reason`.

- [ ] **Step 6: Add failing crash-reconciliation acceptance tests**

Case A: worker session says an action completed but goal checkpoint still marks subgoal `RUNNING`; new coordinator instance must inspect/resume that worker and must not create a second worker session.

Case B: worker session is paused for confirmation; recovery maps parent subgoal to `WAITING` and returns without replay.

- [ ] **Step 7: Implement reconciliation before scheduling**

The worker session is authoritative for its own completed actions. Reuse existing `AgentController` / `AgentSessionStore` reconciliation behavior; do not inspect filesystem ad hoc in the coordinator.

- [ ] **Step 8: Run Task 6 tests plus existing agent acceptance**

Run:

```bash
python -m unittest \
  tests.test_coordinator_controller \
  tests.test_super_agent_end_to_end \
  tests.test_agent_controller \
  tests.test_agent_end_to_end -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add lain/coordinator tests/test_coordinator_controller.py tests/test_super_agent_end_to_end.py
git commit -m "feat: add persistent goal coordinator loop"
```

---

### Task 7: Dependency-Aware Parallel Workers and Audit Provenance

**Files:**
- Modify: `lain/coordinator/controller.py`
- Modify: `lain/runtime/engine.py`
- Modify: `lain/audit/logger.py`
- Modify: `lain/workers/runtime.py`
- Create: `tests/test_parallel_workers.py`
- Modify: `tests/test_runtime.py`
- Create: `tests/test_audit_concurrency.py`

**Interfaces:**
- Consumes: Task 2 scheduler/locks, Task 4 `ScopedRuntime`, Task 6 coordinator.
- Produces:
  - parallel foreground execution bounded by `goal.budget.max_parallel_workers`
  - audit provenance fields `goal_id`, `subgoal_id`, `worker_id`, `plan_version`

Extend trusted runtime call without breaking old callers:

```python
def execute_action(
    self,
    envelope: ActionEnvelope,
    action_id: str,
    *,
    confirmed_action_ids: frozenset[str] = frozenset(),
    provenance: Mapping[str, str | int] | None = None,
) -> ActionResult
```

`ScopedRuntime` injects immutable provenance; worker planners never receive a way to set it.

- [ ] **Step 1: Write failing audit-provenance tests**

Assert old direct runtime calls still work with no provenance and worker runtime audit records contain the four provenance fields.

- [ ] **Step 2: Extend `RuntimeEngine` audit record construction**

Validate provenance keys/types in trusted code. Redaction still applies.

- [ ] **Step 3: Write failing concurrent audit append test**

Start multiple threads appending unique records. Assert exact record count, every line parses, and no record is merged/truncated.

- [ ] **Step 4: Add file locking to `AuditLogger.append`**

Use a sibling lock file or lock the append fd with `fcntl.flock` before `os.write`/`fsync`. Keep `O_APPEND`.

- [ ] **Step 5: Write failing scheduler concurrency tests**

Use blocking fake workers to prove:
- two independent ready subgoals overlap in time
- same claim never overlaps
- max_parallel_workers is honored
- persisted result order is deterministic by original subgoal order, not future completion order

- [ ] **Step 6: Implement bounded `ThreadPoolExecutor` dispatch in `GoalCoordinator.run_until_stop`**

Select ready IDs deterministically, acquire claims before submit, submit at most `max_parallel_workers`, wait for the current batch, then persist all batch results in original subgoal order.

No background thread survives the foreground coordinator call.

- [ ] **Step 7: Run concurrency/audit/runtime regression tests**

Run:

```bash
python -m unittest \
  tests.test_parallel_workers \
  tests.test_audit_concurrency \
  tests.test_runtime \
  tests.test_super_agent_end_to_end -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add lain/coordinator/controller.py lain/runtime/engine.py lain/audit/logger.py lain/workers/runtime.py tests
git commit -m "feat: run independent super-agent workers in parallel"
```

---

### Task 8: Hybrid Goal Budgets, Repeated-Failure Detection, and Replan Cycle Brakes

**Files:**
- Modify: `lain/coordinator/controller.py`
- Modify: `lain/goals/models.py`
- Modify: `lain/config.py`
- Create: `tests/test_goal_budgets.py`
- Create: `tests/test_goal_failure_brakes.py`

**Interfaces:**
- Consumes: `ResourceEnvelope.failure_counts/recent_plan_hashes`, worker session attempted-action counts.
- Produces:

```python
def failure_fingerprint(subgoal: SubgoalState, result: WorkerResult) -> str
def plan_fingerprint(decision: CoordinatorDecision) -> str
```

Use SHA-256 over canonical JSON composed only from stable nonsecret structural fields.

Global defaults come from new `AgentConfig` fields:
- `goal_max_coordinator_iterations = 32`
- `goal_max_total_actions = 128`
- `goal_max_runtime_seconds = 3600.0`
- `goal_max_parallel_workers = 4`
- `goal_max_repeated_failures = 3`

Config keys use `goal_` prefixes matching those names.

Per-goal values may be lower freely. This task does not add a CLI path to exceed global defaults.

- [ ] **Step 1: Write failing config/default tests**

Pin every default and reject booleans, zero/negative, and nonfinite runtime.

- [ ] **Step 2: Wire global defaults into `GoalCoordinator.create`**

If a caller supplies an envelope, reject any field greater than configured global maximum.

- [ ] **Step 3: Write failing aggregate-action/runtime/coordinator-iteration budget tests**

Prove exhausted budgets stop before the next planner call or worker action and transition goal to `BLOCKED` with a structured budget reason.

- [ ] **Step 4: Implement budget accounting**

Aggregate `total_attempted_actions` from newly settled worker checkpoints exactly once.

Measure coordinator/worker active foreground runtime with injected `monotonic_clock` for deterministic tests.

- [ ] **Step 5: Write failing repeated-failure and plan-cycle tests**

Pin:
- same failure fingerprint at `max_repeated_failures` prevents an identical subgoal retry
- identical coordinator plan hash repeated three times without any subgoal progress blocks the goal
- a changed verified world/worker result clears the no-progress plan streak

- [ ] **Step 6: Implement failure/plan fingerprints and no-progress brakes**

Keep only the latest 8 plan hashes in persisted state.

- [ ] **Step 7: Run Task 8 tests**

Run: `python -m unittest tests.test_goal_budgets tests.test_goal_failure_brakes tests.test_coordinator_controller -v`  
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add lain/coordinator/controller.py lain/goals/models.py lain/config.py tests/test_goal_budgets.py tests/test_goal_failure_brakes.py
git commit -m "feat: bound autonomous goal execution"
```

---

### Task 9: CLI Goal Control Plane and Legacy Compatibility

**Files:**
- Modify: `lain/cli.py`
- Modify: `lain/__init__.py` only if public exports are required
- Create: `tests/test_goal_cli.py`
- Modify: `tests/test_agent_cli.py`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: Goal coordinator/store and current agent CLI stack.
- Produces these exact commands:

```text
lain goal run "<objective>" [--json]
lain goal list [--json]
lain goal inspect <goal-id> [--json]
lain goal resume <goal-id> [--json]
lain goal cancel <goal-id> [--json]
lain goal event <goal-id> --kind <kind> --message "<text>" [--json]
```

Keep these existing commands unchanged:

```text
lain run
lain sessions
lain session
lain resume
lain cancel
```

Add:

```python
def _build_goal_stack(config: RuntimeConfig) -> tuple[GoalCoordinator, GoalStore]
def _safe_goal_payload(goal: GoalState) -> dict[str, Any]
```

`_safe_goal_payload` redacts nested worker results/memory/event content using existing redaction helpers.

- [ ] **Step 1: Write failing CLI create/list/inspect tests**

Use temporary workspace and fake planner commands. Pin stable JSON keys and exit codes.

- [ ] **Step 2: Add CLI parser and `_build_goal_stack`**

Goal storage root: `config.audit_path.parent / "goals"`. Worker session storage continues at `config.audit_path.parent / "sessions"`.

- [ ] **Step 3: Write failing event/cancel/resume tests**

`goal event` only appends the event; it never implicitly resumes a blocked goal. `goal resume` performs foreground execution.

- [ ] **Step 4: Implement command dispatch and safe JSON**

No command auto-confirms a waiting worker action.

- [ ] **Step 5: Add legacy compatibility assertions**

Existing `tests/test_agent_cli.py` must remain green without changing expected command behavior.

- [ ] **Step 6: Document the goal path and architecture boundary**

README wording: `lain goal run` is the new mission-level interface; `lain run` remains the bounded single-worker session interface during migration.

- [ ] **Step 7: Run CLI and full portable verification**

Run:

```bash
python -m unittest tests.test_goal_cli tests.test_agent_cli tests.test_cli -v
python scripts/verify.py
```

Expected: all commands exit 0; verifier reports no failures.

- [ ] **Step 8: Commit**

```bash
git add lain/cli.py tests/test_goal_cli.py tests/test_agent_cli.py README.md docs/ARCHITECTURE.md
git commit -m "feat: expose super-agent goal control plane"
```

---

### Task 10: Core Acceptance, Security Regression, and Implementation Handoff

**Files:**
- Modify: `tests/test_super_agent_end_to_end.py`
- Modify: `scripts/verify.py` only if new test discovery requires it
- Create: `docs/SUPER_AGENT.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: every prior task.
- Produces: one end-to-end acceptance story and durable operator/developer documentation.

Acceptance scenario:

1. User starts one goal.
2. Coordinator proposes two independent subgoals plus one dependent subgoal.
3. Two safe workers run concurrently.
4. The dependent worker runs after both complete.
5. A worker action fails once; coordinator receives verified failure state and replans with an alternate subgoal.
6. Process is reconstructed from persisted stores between worker batches.
7. A mid-mission informational event is visible in coordinator context without cancelling work.
8. Final coordinator decision is `complete`.
9. Every executed action has goal/subgoal/worker provenance.
10. No action executes twice.

- [ ] **Step 1: Write the complete end-to-end acceptance test**

Assert final files/state/audit contents, unique execution attempts, final `GoalStatus.COMPLETED`, and model-owned completion reason.

- [ ] **Step 2: Add adversarial acceptance cases**

Add:
- injected out-of-scope worker capability
- cyclic coordinator proposal
- coordinator `complete` with pending work
- conflicting claims
- stale worker/goal checkpoint mismatch
- hostile goal/event text claiming confirmation or authority

- [ ] **Step 3: Run focused acceptance**

Run: `python -m unittest tests.test_super_agent_end_to_end -v`  
Expected: PASS.

- [ ] **Step 4: Run full Python verification**

Run: `python scripts/verify.py`  
Expected: exit 0, all unit tests pass, compile/diff/safety/name checks green.

- [ ] **Step 5: Write `docs/SUPER_AGENT.md`**

Document:
- goal vs worker session
- coordinator loop
- DAG/claims
- model routing
- budgets
- event behavior
- crash recovery
- CLI examples
- current limits
- explicit statement that completion is model-owned but side effects remain trusted-code-owned

- [ ] **Step 6: Verify no placeholders and clean branch diff**

Run:

```bash
grep -RInE 'TODO|TBD|FIXME' lain/goals lain/coordinator lain/workers lain/scheduling lain/memory lain/models docs/SUPER_AGENT.md || true
git diff --check
git status --short
```

Expected: no implementation placeholders; `git diff --check` exits 0; only intentional changes are present.

- [ ] **Step 7: Commit**

```bash
git add tests/test_super_agent_end_to_end.py docs/SUPER_AGENT.md README.md scripts/verify.py
git commit -m "test: prove super-agent core end to end"
```

## Self-Review Result

Spec coverage for the executable core is complete: persistent goal state, coordinator-owned mission planning/completion, generic workers, provider-neutral routing, DAG scheduling, scoped authority, structured memory/context, events, crash reconciliation, parallelism, provenance, hybrid budgets, retry/cycle brakes, and a CLI control plane all map to tasks above.

The Android operator console, richer chat/voice surface, durable external triggers, and UI model/provider settings are intentionally separated into the dependent operator plan because they can be reviewed and shipped independently after the core interfaces are green. Capability acquisition and self-modification remain policy/workflow boundaries in this milestone; this plan does not activate arbitrary code or production self-upgrade, matching the v1 exclusions in the spec.