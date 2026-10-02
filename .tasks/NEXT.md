# Next

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

