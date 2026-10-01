# Security and Threat Model

LAIN_OS can become a privileged automation layer. Security therefore belongs in the architecture, not as a later patch.

## Core rule

**Reasoning does not imply authority.**

A model may propose an action. Only the policy layer can authorize execution.

## Planner boundary

Planner input contains the original intent as data and a catalog derived from the capability registry. Planner output is accepted only as one exact JSON document containing a bounded, non-empty list of capability names and arguments; fenced JSON, prose, extra fields, unknown capabilities, and invalid arguments fail closed. The trusted layer—not the planner—creates the ACTION_PROTOCOL version, UUID request ID, preserved intent, and `a1`, `a2`, ... action IDs.

The external-process adapter is provider-independent and executes only administrator-configured argv with `shell=False`. It has timeout and output limits and bounds stderr diagnostics. The configured executable is not an ACTION_PROTOCOL capability. Prompt instructions reinforce this separation, but validation and policy enforcement provide the security boundary. Planner text cannot confer permissions, lower risk, satisfy confirmation, select an executor, claim verification, or change auditing.

## Autonomous-loop boundary

Autonomous loops extend duration and continuity, not authority.

The controller enforces finite trusted budgets independently of planner cooperation. Defaults are 12 planner iterations, 32 attempted actions total, 900 seconds of active planner/executor runtime, and at most the configured planner action limit per batch. Resume never resets consumed budgets.

A planner cannot satisfy confirmation. When policy returns `confirmation_required`, the current batch stops and the session persists `paused_confirmation`. Only an explicit trusted action ID supplied by the user can retry that exact action.

Each session has an exclusive non-blocking file lease while a controller invocation is advancing it. Concurrent resume attempts fail before planner or executor work, preventing two processes from racing the same durable state.

Every executed action is checkpointed before another action may run. Completed verified actions are never blindly replayed after restart. Existing runtime action/request idempotency remains authoritative.

Crash recovery is deliberately conservative. If the append-only audit says the current action was execution-attempted but the session checkpoint still lacks its result, LAIN_OS does not infer success and does not retry. The session blocks with reconciliation required. This protects external writes and any other action whose outcome could be ambiguous across a crash boundary.

Session/planner-facing output uses the existing recursive redaction rules for credential-like keys and private payload keys such as `content` and `body`. Durable session files must not contain credentials.

## Primary threats

### Prompt injection

Untrusted text may attempt to alter agent behavior.

Sources include:
- websites;
- PDFs;
- emails;
- notifications;
- repository contents;
- accessibility trees.

Mitigation:
- treat retrieved content as data;
- never allow content to redefine capability policy;
- require typed action generation;
- validate every action independently.

### Excessive privilege

An executor with broad shell, AccessibilityService, or Shizuku access can affect the entire device.

Mitigation:
- expose narrow capability wrappers;
- separate read and write capabilities;
- default-deny unknown actions;
- require explicit confirmation for sensitive operations.

### Secret leakage

Models, logs, repositories, or remote APIs may accidentally receive secrets.

Mitigation:
- redact sensitive parameters;
- never log tokens or recovery codes;
- keep secrets outside the repository;
- avoid including unrelated device context in model prompts.

### Destructive automation

A valid action may still cause unacceptable damage.

Mitigation:
- prefer reversible actions;
- use trash/quarantine before deletion;
- preview bulk operations;
- require confirmation for destructive actions;
- verify postconditions.

### Silent failure

Automation that claims success without actually succeeding corrupts trust.

Mitigation:
- structured executor results;
- independent verification;
- explicit failure states;
- no "best effort" success reporting.

## Capability risk classes

### Class 0 — Read-only
Examples: list files, inspect battery state.

Default: allowed when explicitly requested.

### Class 1 — Reversible local write
Examples: create note, copy file, post notification.

Default: may be automatable under user policy.

### Class 2 — External or consequential write
Examples: send message, publish Git commit, modify account state.

Default: confirmation required unless the user explicitly configures a trusted workflow.

### Class 3 — Destructive or high-sensitivity
Examples: delete data, change security settings, expose private information.

Default: explicit per-action approval.

## Logging

Audit logs must describe what happened without becoming a secondary leak.

Store:
- action type;
- timestamp;
- redacted arguments;
- executor;
- outcome;
- verification result.

Do not store:
- passwords;
- access tokens;
- recovery codes;
- full private message bodies unless explicitly required;
- precise historical location unless the user intentionally enables it.

## Authenticated external writes

`reddit.create_post` is Class 2 and always requires confirmation under the default policy. Planner intent cannot grant that confirmation. OAuth client credentials and refresh tokens are read from `LAIN_REDDIT_*` environment variables, are never accepted in an action envelope, and are never included in results or audit records. Post bodies are redacted from audit arguments.

Live Reddit posting has not been performed as part of the planner milestone. Android notification, URI opening, and audit recording have been manually hardware-validated in F-Droid Termux with Termux:API; no automated Android CI is claimed.

An attempted request ID is terminal even after timeout or an ambiguous remote failure: the runtime writes an audit idempotency barrier before calling the remote submit endpoint and will not submit that ID again merely to determine whether the first request succeeded. Rate-limit responses are returned without credential rotation or aggressive retries. This narrow adapter does not create a general HTTP or raw Reddit capability.
