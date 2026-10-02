# Next

## TASK-001: Reconcile PR #4 with current main and re-run acceptance
**Priority:** P0
**Updated:** 2026-10-02 01:40

PR #4 contains the Android Stop cancellation wake-up fix, but its head `04b96f64ea5ce18c09089dd48c8d9d0f484f3b04` is now diverged from current `main`.

Rebase or otherwise reconcile the PR branch onto the current mainline, run the canonical Verify and Android CI gates on the reconciled head, then repeat the physical Stop-at-confirmation-transition acceptance from `docs/ANDROID_DEVICE_ACCEPTANCE.md`. Preserve the pluggable-planner work already merged through PR #5.

Do not merge without explicit owner approval and fresh final-head evidence.

---

## TASK-002: Implement Android Keystore-backed planner SecretStore
**Priority:** P1
**Updated:** 2026-10-02 01:40

Implement Phase 2 P2-03: Android-native credential persistence for planner profiles using opaque credential references.

Acceptance:
- credential survives app restart;
- raw secret never appears in Python durable state, Binder/IPC responses, audit, logs, screenshots/settings export, or planner context;
- replace and remove operations work;
- missing credential produces an explicit configuration failure;
- focused leakage and adversarial tests cover the boundary;
- existing backup/device-transfer exclusion posture remains intact.

---

## TASK-003: Implement bounded native planner transport
**Priority:** P1
**Updated:** 2026-10-02 01:40

Implement Phase 2 P2-04 after TASK-002: cancellable Android-native HTTP transport shared by Cloud and Local OpenAI-compatible planner profiles.

Acceptance:
- timeout and response-size bounds are enforced;
- structured failures cover DNS/unreachable, refused connection, TLS, 401/403, missing model/404, timeout, 429, 5xx, cancellation, oversized response, and malformed/unsupported responses;
- Local mode never silently falls back to Cloud;
- plaintext LAN HTTP is allowed only under the documented explicit local/private-address policy;
- cancellation cannot lead to subsequent action execution.

---
