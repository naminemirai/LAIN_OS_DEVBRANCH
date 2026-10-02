# In Progress

## TASK-001: Reconcile PR #4 with current main and restore mergeability
**Priority:** P0
**Updated:** 2026-10-02 15:17

Fresh GitHub PR review on head `6217be8ec2b3d4bd20993c46239bf0425543617c` passed with no actionable code finding, and Android workflow #22 plus Verify workflow #33 are successful. GitHub currently reports the PR non-mergeable because the branch has diverged from current `main@f96bd6e6429faaf8a7d8af5a753b66b46e4511b9` (2 commits ahead, 11 behind).

Acceptance:
- reconcile the PR branch with current main without dropping the intended seven-file Android Stop wake-up fix;
- restore GitHub mergeability;
- preserve unrelated mainline work;
- request/perform a fresh PR review on the reconciled head;
- if that fresh review passes, the owner-authorized review-only merge policy permits merge even if physical acceptance/tests are not rerun; any deferred/unrun checks must remain explicitly labeled rather than claimed passed.

### Plan

- Reconcile the feature branch with current main without losing the Stop wake-up changes.
- Re-establish review evidence on the reconciled head.
- Keep any deferred/unrun checks explicitly labeled.

### Blocker

2026-10-02 15:17 — Current owner authority explicitly forbids merge, rebase/history rewrite, force-update, or another consequential irreversible branch reconciliation without separate explicit authorization. No reconciliation mutation was performed. TASK-001 remains In Progress and blocked; independent safe work continues.

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


### Plan

- Define a narrow native planner transport contract consuming PlannerBinding plus SecretStore.
- Implement cancellable bounded OpenAI-compatible HTTP POST for cloud/local profiles.
- Map DNS/refused/TLS/auth/not-found/timeout/rate-limit/5xx/cancel/oversize/malformed failures to structured native codes.
- Enforce no cloud fallback and explicit private-address cleartext policy from the existing binding.
- Author focused Android tests but defer running verification per owner directive.
- Open a PR, hand it to review, record deferred checks, then advance.

---
