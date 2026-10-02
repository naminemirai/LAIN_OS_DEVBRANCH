# In Progress

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
