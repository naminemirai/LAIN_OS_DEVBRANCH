# In Progress

## TASK-004: Complete open LAIN engineering workflow migration
**Priority:** P1
**Updated:** 2026-10-02 20:56

Complete PR #9's migration from person-specific ZzzOps engineering skills to
functional LAIN workflow names without weakening safety boundaries.

### Sequence

1. **Make the migration contract executable (completed).**
   - Observable outcome: every contract assertion is discovered by the canonical
     `unittest` runner and compares parsed skill metadata and resolved feedback
     targets, not substrings.
   - Dependencies: none.
   - Verification: run the focused contract test through `python -m unittest`.
   - Expected result: the test is discovered and fails because the
     `plugins/lain-engineering` implementation is not yet present.
2. **Implement the bounded migration (next).**
   - Observable outcome: the functional skill tree and neutral plugin manifests
     exist, feedback targets are repository/configuration-derived, and policy
     approval is iterative while unresolved safety decisions remain blocking.
   - Dependencies: executable red contract from step 1.
   - Verification: run the focused contract test and inspect the complete diff
     for retired invocations and preserved safety boundaries.
   - Expected result: the focused contract passes with no person-specific or
     retired skill identifiers.
3. **Run repository gates and re-review PR #9.**
   - Observable outcome: canonical verification exercises the contract and a
     fresh whole-diff review has no correctness or safety blocker.
   - Dependencies: step 2.
   - Verification: `python scripts/verify.py`, required CI, and fresh PR review.
   - Expected result: checks pass with explicit status and the PR is merge-ready
     under the review-only policy.

### Evidence / progress

- PR #9 head `2dde8da3ac4aedf52cdb76ef65ddd320325ff039` now uses
  discoverable `unittest.TestCase` coverage, exact parsed frontmatter names,
  and repository-derived feedback-target cases for HTTPS and SSH origins.
- Focused canonical execution discovers 5 tests and fails all 5 for the intended
  red-state reason: `plugins/lain-engineering` is absent.
- Fresh review still does not pass (review ID `5398246491`). Verify #67 now
  fails the expected 5 discovered contract tests because the plugin is absent;
  Android #56 remains in progress and is not claimed passed. No merge was
  performed.

---

## TASK-003: Implement bounded native planner transport
**Priority:** P1
**Updated:** 2026-10-02 18:59

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
- Android workflow #51 failed on both API jobs in
  `NativePlannerTransportTest.rejectsOversizedMalformedAndUnsupportedResponses`;
  the malformed-response case returned a non-failure and the forced cast failed at
  test line 130. Instrumentation was skipped.
- Fresh GitHub review on head `7316494` does not pass (review ID
  `5397679657`); PR #8 remains draft and non-mergeable.

### Blockers / deferred verification

- The JVM test exercises Android `org.json.JSONObject` through local Android
  stubs, so its malformed-JSON assertion is not truthful in that environment.
  Validation must become platform-neutral for JVM coverage or move to Android
  instrumentation before the workflow can pass.
- Arbitrary user-entered private-LAN HTTP remains blocked by Android's global cleartext deny. The transport validates explicit Local/private-address opt-in, but enabling dynamic RFC1918 cleartext would require a material security/compatibility decision; this branch does not globally weaken cleartext policy or bypass it with raw sockets.
- The accepted-binding/runtime-policy mismatch must be resolved: reject Local
  cleartext at the binding boundary for this release, or implement a narrowly safe
  Android policy. Global cleartext enablement and raw-socket bypass remain rejected.
- Verify workflow #62 passed. Android workflow #51 failed; Android
  instrumentation and any later skipped steps remain untested.

### Sequenced continuation

- Observable outcome: Local HTTP validation and Android runtime policy describe
  one truthful supported contract, and malformed JSON is validated on a
  platform-neutral boundary or truthful instrumentation path.
- Dependencies: explicit cleartext compatibility/security decision.
- Verification: focused malformed-response test, Android workflow, manifest
  policy test, and fresh whole-diff review.
- Expected result: accepted planner bindings are executable under Android policy,
  the failing JVM assertion is truthful, and the review passes without weakening
  global cleartext protections.
- Fresh unchanged-head review remains blocked (review ID `5398033574`).

---
