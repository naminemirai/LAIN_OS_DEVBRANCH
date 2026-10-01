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
