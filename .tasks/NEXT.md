# Next

## TASK-001: Reconcile PR #4 with current main and restore mergeability
**Priority:** P0
**Updated:** 2026-10-02 12:19

Fresh GitHub PR review on head `6217be8ec2b3d4bd20993c46239bf0425543617c` passed with no actionable code finding, and Android workflow #22 plus Verify workflow #33 are successful. GitHub currently reports the PR non-mergeable because the branch has diverged from current `main@f96bd6e6429faaf8a7d8af5a753b66b46e4511b9` (2 commits ahead, 11 behind).

Acceptance:
- reconcile the PR branch with current main without dropping the intended seven-file Android Stop wake-up fix;
- restore GitHub mergeability;
- preserve unrelated mainline work;
- request/perform a fresh PR review on the reconciled head;
- if that fresh review passes, the owner-authorized review-only merge policy permits merge even if physical acceptance/tests are not rerun; any deferred/unrun checks must remain explicitly labeled rather than claimed passed.

---

## TASK-002: Implement Android Keystore-backed planner SecretStore
**Priority:** P1
**Updated:** 2026-10-02 12:19

Fresh GitHub PR review of PR #7 head `f41f8acf26a89b936b8eb8da5eca3f9581cab779` did not pass.

Required corrections:
- bind each encrypted credential record to its exact `credential_ref` (and preferably record version/domain separator) with AES-GCM AAD on both encryption and decryption;
- add an adversarial swapped/renamed-record test that fails closed;
- fix the first-use `planner-secrets` directory creation race by re-checking `isDirectory` when `mkdirs()` returns false;
- add a concurrent-initialization regression if practical;
- preserve the native-only secret boundary and existing backup/device-transfer posture.

Acceptance:
- both review findings are addressed on the PR branch;
- authored tests cover the fixes; under the owner's current review policy, unrun tests remain explicitly labeled untested rather than passed;
- a fresh GitHub PR review passes before merge.

---
