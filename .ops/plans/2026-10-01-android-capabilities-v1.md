# Android Capability Expansion v1

Base: upstream main `24ec1621fd63aaa6ce74f34c322d7b371b823ff6`.
The user's session specification is authoritative; native continuous execution
is authorized without routine design/plan approval pauses.

## Design

Preserve planner → registry → policy → runtime → verification → audit → checkpoint.
Extend ArgumentSpec with bounded integers/text validation. Add only the five
named capabilities; share chooser is Class 2, explicitly confirmed, offline.
Use a private reusable Android command boundary, fixed argv, stdin for payloads,
allowlisted environment, timeout and actively bounded stdout/stderr. Existing
notification and URI adapters reuse the boundary without changing launch order.
Battery fields are validated and filtered; its verifier revalidates the structured
evidence. Clipboard readback compares only the just-written value privately;
no raw stdout/stderr, content, or readback appears in outcomes. Other effects
have LIMITED verification. No generic shell, HTTP, intent or clipboard-read
capability is exposed.

## Tasks (RED → GREEN → REFACTOR)

1. Registry: names, risk/confirmation, argument types/unknown fields and bounds.
2. Boundary: bounded subprocess I/O, stdin, fixed environment, timeout/nonzero/
   unsupported errors; regress notification and URI behavior.
3. Adapters/verifiers: battery parse/filter; bounded vibrate; short toast; private
   clipboard readback; share chooser with no receiver/default selection.
4. Runtime/autonomy: explicit dispatch, verification, policy confirmation and
   denial, checkpoint and redacted planner/session/audit views.
5. Docs: actual live Groq evidence, capabilities and limitations, safe hardware
   acceptance sequence, command availability helper.
6. Full verifier, fresh independent review/fixes, connector-backed Git commit
   and branch publication, PR, exact-head GitHub CI/review/mergeability evidence.

## Review focus

Hostile leading options, Unicode/NUL and byte bounds; stderr and clipboard
leakage; readback mismatch versus unavailable; no chooser bypass; process
descendant cleanup; planner self-confirmation; preservation of existing behavior.

## Evidence

Baseline: `python scripts/verify.py` → 198 tests passing; compile/diff/security
checks passing. Connector-retrieved files produce the exact upstream Git tree
`90d42323964f051b0dcc2e69e2a21b3679c4fab3`.

Implementation and regression tests were developed in RED → GREEN steps for
registry bounds, all adapters, command output/timeout limits, runtime/autonomous
dispatch, clipboard public display, and the Android availability helper.

Fresh independent review found two Important issues: incorrect clipboard LF
comparison and private payload echoes in free-text views. Both have observed
RED → GREEN regression tests. Follow-up checks also cover masking multiple
payloads without changing structural metadata, optional battery percentage and
unknown platform enums, and publication of argument limits to planners/CLI while
preserving the existing Groq argument contract.

Rulings:
- Preserve exact private mode-0600 session checkpoint payloads, including completed
  actions; redact public/planner views. Changing durable replay state would exceed
  this milestone. Cost: a device owner/local privileged process can read retained
  payloads; checkpoints must stay private.
- Initial user goal remains available to the first planner call so it can propose
  explicit content; subsequent known payload echoes are masked. Cost: users must
  not supply credentials as goals/payloads.
- Existing Termux toast upstream uses `echo` and may consume option-only strings
  such as `-n`. Keep command-acceptance LIMITED and document the fidelity limit.
  Cost: such a toast may appear empty; ordinary marker hardware test remains needed.
- POSIX process-group cleanup covers ordinary descendants, not intentionally
  daemonized processes escaping the group. Capability-selected installed commands
  are trusted; no planner-controlled executable exists.

Review source contracts checked at Termux API
`fc26ce17e3badf85d4df191af364fcf7798047f1` and API package
`9e7f1531e1aa4a9c1e261a2dbde4de93653c366e`: ClipboardAPI prints exact text with no
delimiter and v2 stdin preserves whitespace; share stdin path always creates a
chooser. This source inspection is not physical Android validation.

GitHub connector became unavailable after successful exact-base retrieval;
discovery reports GitHub uninstalled. No PR, CI status or mergeability evidence is
claimed until installation/connection is restored. The existing branch and
review fixes are retained together; no follow-up PR or merge is authorized.


## Completion record

Subsequent execution superseded the earlier publication-status note above without
rewriting that historical record. PR #1 was published and later merged into
`main` as merge commit `4f718038db6065328895b261c92ae7504ca25aad`.

Manual Android/Termux acceptance completed at exact feature head
`0d7efe584b78a050c2817b2ab3e3f555e2450dff`: battery and clipboard verification
PASSED; toast, vibration, and share reported LIMITED as designed; unconfirmed share
was blocked by policy; the user observed the toast, vibration, and share chooser;
and audit content redaction was confirmed. GitHub Actions Verify run #7 passed on
the accepted feature head, and Verify run #8 passed on the merge commit with 232
tests.

The completed acceptance is manual physical-device evidence, not automated Android
hardware CI. Later runtime-affecting Android changes require a fresh hardware gate.
