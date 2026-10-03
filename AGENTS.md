<!-- TASKPLANNER:START -->
# TaskPlanner — AI Agent Instructions

Tasks live as Markdown under `.tasks/`. Prefer TaskPlanner MCP tools when available; otherwise use the direct-file workflow without changing unrelated tasks.

## States

- **Backlog** → `BACKLOG.md`
- **Next** → `NEXT.md`
- **In Progress** → `IN_PROGRESS.md`
- **Done** → `DONE.md`
- **Rejected** → `REJECTED.md`
- **Work Log** → `WORK_LOG.md` (optional completion log, not a task state)

## Task format

```markdown
## TASK-001: Task title
**Priority:** P1 | **Tags:** tag1, tag2

Description.

---
```

ID prefix: `TASK`. Priorities: P0, P1, P2, P3, P4. This project currently has no predefined tag list.

## Workflow

1. Pick the highest-priority task from Next, then Backlog, unless the user chose one.
2. Move the complete task section to `IN_PROGRESS.md` before substantive implementation.
3. Because `aiPlanRequired` is true, add a concise `### Plan` (about 3–7 bullets) before coding.
4. Implement and verify the work.
5. Move the task to `DONE.md`, keeping a condensed `### Plan` as the done-summary.
6. Add one short entry at the top of `.tasks/WORK_LOG.md` when it exists.
7. Add a `CHANGELOG.md` entry under `## [Unreleased]` when repository guidance requires it.

## Tool preference

Use `taskplanner_list` / `taskplanner_board`, `taskplanner_get`, `taskplanner_create`, `taskplanner_move`, and `taskplanner_update` when the host exposes them for this workspace. Check once per session. If unavailable, edit the Markdown files directly and preserve UTF-8, task IDs, separators, and unrelated sections.

## Creating tasks without MCP tools

1. Read `.tasks/config.json` for `idPrefix` and `nextId`.
2. Allocate `{idPrefix}-{nextId padded to 3 digits}`.
3. Increment and save `nextId`.
4. Insert the complete task section at the top of the selected state file, directly after its `# Heading`.
5. Default priority is P2 when the user does not specify one. Tags are optional. Set `**Updated:** YYYY-MM-DD HH:mm`.
6. End every task with `---`.

## Rules

- Never change task IDs.
- Never modify unrelated task sections.
- Move the whole task section, including its trailing `---`.
- Preserve user configuration choices and unknown fields in `.tasks/config.json`.
- A plan is required before coding and should be condensed, not deleted, on completion.

<!-- TASKPLANNER:END -->

## Documentation boundary

Keep product and organizational concerns separate.

- Product documentation: `README.md`, `docs/`, and `specs/`. Describe LAIN_OS behavior, architecture, interfaces, security, acceptance, and release goals only.
- Internal engineering operations: `.ops/`, `.tasks/`, this file, and GitHub coordination surfaces. Put task sequencing, agent prompts, review/merge policy, scheduled automation, role instructions, and other development-process material here.
- Never copy internal operating parameters into product documentation.
- Preserved historical implementation sources are indexed in `.ops/README.md`.
