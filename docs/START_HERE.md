# Start here — Job Finder handoff v1.1

**30 October 2026.** UI-first is confirmed. This revision contains ten Markdown files and replaces the previous handoff's open milestone decision.

## Place the files

Merge the ZIP contents into the project parent folder, not into either `src/` directory:

```text
project-name/
  AGENTS.md
  frontend/
    AGENTS.md
    CONTEXT.md
    README.md
  backend/
    AGENTS.md
    CONTEXT.md
    README.md
    docs/
      ARCHITECTURE.md
      PLAN.md
      START_HERE.md
```

Keep frontend/backend as separate Git repos. Preserve useful existing instructions and README content. If v1.0 was already merged, move any local additions from `backend/docs/CONTEXT.md` into `backend/CONTEXT.md` and retire the superseded copy; do not leave two conflicting active contexts.

## First local-agent prompt

```text
Perform T00 only for this workspace. Do not start feature implementation.

First read ./AGENTS.md, then frontend/AGENTS.md, frontend/CONTEXT.md,
frontend/README.md, backend/AGENTS.md, backend/CONTEXT.md, backend/README.md,
backend/docs/ARCHITECTURE.md, and backend/docs/PLAN.md.
Confirm which instruction files you actually read.

Inspect both existing repositories and verify available non-destructive
startup/check commands. Record actual local conventions in the marked
Observed conventions sections of each repo's AGENTS.md. Update README
verification tables and CONTEXT implementation status using evidence only.

UI-first is fixed: coherent mock workflows first, then verified real APIs
and removal of each migrated feature's obsolete runtime mock references.
Preserve efficient, DRY, modular, readable, functional code requirements.

Edit documentation only. Do not change source code, dependencies, lockfiles,
configuration, environment values, or Git history. Do not re-scaffold.
Do not weaken fixed instructions or invent commands/test results.

Return a concise report: files read; observed structure; documentation
changed; checks/results; conflicts/blockers; and the next scoped UI task.
Then stop. Do not begin T01 or consume the backlog automatically.
```

This run verifies the instruction chain and setup; it does not prove that future feature code is correct. Review its report before assigning the next UI task.
