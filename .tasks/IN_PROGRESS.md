# In Progress

## TASK-003: Implement bounded native planner transport
**Priority:** P1
**Updated:** 2026-10-02 18:53

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


### Progress

- Branch `feature/task-003-native-planner-transport` fast-forwarded to `main@4f6f6bc` without history rewrite.
- Draft PR #8 opened at head `7316494`.
- Authored JVM transport tests and Android manifest-policy instrumentation tests.
- Implemented bounded/cancellable OpenAI-compatible native HTTP transport using existing `SecretStore`; no provider SDK dependency added.
- Added Android `INTERNET` permission while preserving global cleartext deny.
- Structured failure mapping covers required DNS/unreachable, refused, TLS, 401/403, 404, timeout/408, 429, 5xx, cancellation, oversized, malformed, and unsupported response cases.
- Verify workflow #62 completed successfully on PR head `7316494`.
- Android workflow #51 is currently in progress at build/unit/lint on API 24 and 35; no Android pass claim yet.

### Blockers / deferred verification

- `gh-review-loop` is blocked in this runtime because `gh` is unavailable (`gh: command not found`, exit 127); no alternate reviewer state was inferred.
- Arbitrary user-entered private-LAN HTTP remains blocked by Android's global cleartext deny. The transport validates explicit Local/private-address opt-in, but enabling dynamic RFC1918 cleartext would require a material security/compatibility decision; this branch does not globally weaken cleartext policy or bypass it with raw sockets.
- Android build, JVM tests, instrumentation, and lint remain UNVERIFIED until workflow #51 completes; tests were authored before production changes but not locally executed under the build-first directive.

---
