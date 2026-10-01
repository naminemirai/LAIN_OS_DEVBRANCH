# Android Capability Expansion v1 — manual hardware gate

Run on real F-Droid Termux plus matching Termux:API. This document records the
completed v1 acceptance and remains the procedure for future revalidation. Execute
one step, inspect its result, then continue. Do not install from a moving branch
without checking the exact reviewed SHA. No credential contents are printed or
changed here.

## Acceptance record

Manual acceptance completed on Android 16 at exact feature head
`0d7efe584b78a050c2817b2ab3e3f555e2450dff`, later merged unchanged into
`main` by merge commit `4f718038db6065328895b261c92ae7504ca25aad`.

Observed results:

- `android.battery_status`: success, verification PASSED.
- `android.toast`: success, verification LIMITED; toast physically observed.
- `android.vibrate`: success, verification LIMITED; vibration physically observed.
- `android.clipboard_set`: success, verification PASSED.
- `android.share_text`: unconfirmed execution blocked with
  `CONFIRMATION_REQUIRED`; after explicit confirmation, success + LIMITED and the
  Android share chooser appeared. No destination was selected and nothing was sent.
- Audit records redacted clipboard/share `content` as `[REDACTED]` and preserved
  the expected risk and policy decisions.

GitHub Actions Verify run #7 passed on the accepted feature head. The merge commit
then passed Verify run #8 with 232 tests. This is manual hardware evidence plus
portable CI, not automated Android hardware CI.

The physical timeout found during acceptance was traced to the filtered subprocess
environment omitting Android runtime variables required by Termux:API on Android
16. The accepted head preserves those required runtime variables while continuing
to exclude provider/executor credentials.

Any later runtime-affecting change to the Android command transport, adapters,
policy, verification semantics, command arguments, environment propagation,
clipboard handling, or share behavior requires a fresh hardware acceptance run.

## 1. Confirm exact PR head

From the existing repository, run this first command and compare its full SHA
with the final PR report:

```sh
git ls-remote origin refs/heads/feature/android-capabilities-v1
```

Do not continue unless it matches. The PR must first have green CI, completed
review and a reported head SHA; these instructions alone are not merge-readiness.

## 2. Isolated worktree

```sh
git fetch origin feature/android-capabilities-v1
```

```sh
LAIN_HW_HEAD=$(git rev-parse FETCH_HEAD)
git worktree add --detach "$HOME/lain-android-v1-${LAIN_HW_HEAD}" "$LAIN_HW_HEAD"
```

```sh
cd "$HOME/lain-android-v1-${LAIN_HW_HEAD}"
git rev-parse HEAD
```

Compare again. Commands below use `python -m lain` from this worktree, avoiding
an older installed console script. No global package/configuration changes needed.

## 3. Non-destructive helper and isolated request fixtures

```sh
python scripts/verify_android.py
```

Expected: portable suite and scans pass. Missing commands are informational in
this helper, but a device acceptance action needs its matching command.

Create an isolated temporary workspace containing harmless test requests only:

```sh
LAIN_HW_WORKSPACE=$(mktemp -d "$HOME/lain-android-v1-test.XXXXXX")
export LAIN_HW_WORKSPACE
python - <<'PY'
import json, os, uuid
from pathlib import Path
root = Path(os.environ['LAIN_HW_WORKSPACE'])
fixtures = (
    ('battery', 'android.battery_status', {}),
    ('toast', 'android.toast', {'content': 'LAIN_OS Android v1 test'}),
    ('vibrate', 'android.vibrate', {'duration_ms': 100}),
    ('clipboard', 'android.clipboard_set', {'content': 'LAIN_OS_SAFE_CLIPBOARD_MARKER'}),
    ('share', 'android.share_text', {'content': 'LAIN_OS harmless chooser test; do not send'}),
)
for stem, name, args in fixtures:
    request = {'version': '0', 'request_id': str(uuid.uuid4()),
               'intent': 'manual Android acceptance',
               'actions': [{'id': 'a1', 'type': name, 'arguments': args}]}
    (root / (stem + '.json')).write_text(json.dumps(request), encoding='utf-8')
print('Harmless request fixtures prepared in isolated workspace.')
PY
```

Requests are single-use. To repeat tests, prepare a fresh temporary workspace;
do not circumvent duplicate-request protection or delete audit records.

## 4. Battery

```sh
python -m lain --workspace "$LAIN_HW_WORKSPACE" execute "$LAIN_HW_WORKSPACE/battery.json" --json
```

Expected: success with conservative battery fields and PASSED structured-evidence
verification. Check percentage against the device; PASSED does not prove sensor
calibration. Unsupported/failure is a stop to inspect prerequisites/output format.

## 5. Short toast

```sh
python -m lain --workspace "$LAIN_HW_WORKSPACE" execute "$LAIN_HW_WORKSPACE/toast.json" --json
```

Observe the short local message. Upstream `termux-toast` uses Bash `echo`, so
option-only text such as `-n` can display empty; command acceptance cannot establish
text fidelity. This test uses an ordinary explicit marker. Expected: success + LIMITED. Record whether it
appeared; do not relabel command acceptance as independent UI verification.

## 6. Short vibration

```sh
python -m lain --workspace "$LAIN_HW_WORKSPACE" execute "$LAIN_HW_WORKSPACE/vibrate.json" --json
```

Expected: success + LIMITED; observe 100-ms vibration where device mode permits.
The adapter does not force vibration in silent mode.

## 7. Explicit harmless clipboard marker

This deliberately replaces current clipboard text with the marker; it never reads
or returns the previous clipboard. Run when that local overwrite is acceptable.

```sh
python -m lain --workspace "$LAIN_HW_WORKSPACE" execute "$LAIN_HW_WORKSPACE/clipboard.json" --json
```

Expected: PASSED on private immediate comparison, LIMITED when Android denies/
lacks readback, or FAILED/VERIFICATION_FAILED on mismatch. Output must not contain
the marker or any unrelated clipboard content. Do not run a generic clipboard
getter or paste private readback into chat. Record the exact verification status.

## 8. Share chooser only

First prove that unconfirmed execution does not launch a chooser:

```sh
python -m lain --workspace "$LAIN_HW_WORKSPACE" execute "$LAIN_HW_WORKSPACE/share.json" --json
```

Expected: confirmation_required, no execution. Then authorize this exact action:

```sh
python -m lain --workspace "$LAIN_HW_WORKSPACE" execute "$LAIN_HW_WORKSPACE/share.json" --confirm a1 --json
```

Expected: only a user-visible chooser, success + LIMITED. Dismiss it. Do not select
a destination or send anything. LAIN_OS must not automatically send content.

## 9. Audit redaction / statuses

```sh
python -m lain --workspace "$LAIN_HW_WORKSPACE" audit tail --limit 20 --json
```

Clipboard/share `content` must be `[REDACTED]`; raw stdout/stderr or clipboard
readback must be absent. Battery is PASSED only with valid evidence. UI/haptic
effects are LIMITED. Share has a confirmation record and a Class 2 pre-execution
barrier plus final result. Do not change statuses manually.

## 10. Optional real Groq loop

Only after deterministic acceptance, reuse the user's existing secure Groq
configuration. Do not display/edit/copy its key file. This command reads battery
and requests a local short toast; it sends the normal planner context to Groq:

```sh
python -m lain --config "$HOME/.config/lain/config.toml" run "Read battery status, display a short local toast saying LAIN_OS Android v1 test, then complete. Do not use other capabilities." --json
```

Inspect trusted action history, verification and final checkpoint. Existing
policy/confirmation/budgets remain authoritative. This is optional networked
planner acceptance, not a prerequisite for offline deterministic capabilities.

For future runtime-affecting changes, repeat this procedure against the new exact
reviewed head and preserve the resulting evidence through review. No automatic
cleanup or modification of unrelated user data is performed.
