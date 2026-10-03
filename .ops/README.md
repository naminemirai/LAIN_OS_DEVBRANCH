# Internal Engineering Operations

This directory contains LAIN_OS development-process material that is intentionally separate from product documentation.

## Boundary

Product documentation lives in `README.md`, `docs/`, and `specs/` and describes the application: product behavior, architecture, protocols, security properties, user-facing configuration, acceptance criteria, and release goals.

Internal development operations live here or in other explicitly internal surfaces such as `.tasks/` and `AGENTS.md`. These may describe implementation sequencing, review/merge procedure, agent prompts, task tracking, automation, developer roles, and historical engineering workflow.

Do not copy internal operating procedure into product documentation.

## Preserved sources

- `.ops/agent-prompts/android-capability-v1-one-shot.md`
- `.ops/plans/2026-09-29-autonomous-loops-v1.md`
- `.ops/plans/2026-09-29-v0-runtime.md`
- `.ops/plans/2026-10-01-android-capabilities-v1.md`
- `.ops/plans/2026-10-01-android-interface.md`

These files were relocated from `docs/` without discarding their source content so future development runs can still retrieve and use them.

## Other internal state

- `.tasks/` — durable TaskPlanner state.
- `AGENTS.md` — repository instructions for engineering agents.
- GitHub issues, pull requests, workflows, and reviews — engineering coordination/evidence surfaces.

Product roadmap: `docs/ROADMAP_1.0.md`.
