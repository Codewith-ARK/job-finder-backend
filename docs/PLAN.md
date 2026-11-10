# Plan — UI-first

**Decision confirmed:** visualize the complete application workflow with mock data first; connect real APIs feature by feature afterward. Architecture v0.2 remains approved. Assign a task or explicit sequence; this document does not start implementation automatically.

## T00 — First-run inspection and local instructions

**Ready. Scope:** read both repos; edit only README files, repository CONTEXT files, the Observed conventions sections of repository AGENTS files, and this task's status. Root fixed rules and application/configuration files stay unchanged.

Read root/scoped instructions first. Inspect manifests, lockfiles, actual folders, existing utilities, safe environment examples, and Git status. Verify available non-destructive startup/check commands. Do not install packages, regenerate lockfiles, edit secrets, or modify source code to complete the audit.

**Done:** READMEs contain verified commands or explicit unknowns; contexts distinguish existing from planned behavior; observed conventions are grounded in actual files; changes are documentation only. Report architectural conflicts and the next UI task, then stop.

## T01 — Frontend foundation for mock workflows

**Next after T00; assign explicitly. Scope:** frontend layouts, providers, shared UI, Query/Axios configuration, mock infrastructure, and relevant checks. Backend edits are excluded.

Create navigation and workspace shells, one stable QueryClient, and explicit development mock adapters behind feature API functions. Keep marketing independent. Use coherent shared mock state; keep feature-specific fixtures with their feature. No backend connection is required to demonstrate mock-only screens.

**Done:** navigation works; mock mode is visibly identified; relevant checks pass; UI does not issue unnecessary real requests.

## T02 — Complete the mock UI milestone

This is a sequence of small tasks, not one unrestricted edit. Give each subtask exact allowed files and acceptance checks before coding.

| Subtask | Outcome |
| --- | --- |
| T02.1 | Account/onboarding/profile and candidate workspace |
| T02.2 | Staff, employee CRUD, teams, supervisor and assignment views |
| T02.3 | Jobs/application workflows with updates visible across roles |
| T02.4 | Platform shell and discussed future-feature previews |

Scope each subtask to its frontend feature, routes, mock records, and related checks. Core interactions update coherent mock state. Include loading/empty/error/success states. External integrations remain clearly unconnected previews.

**Milestone done:** the owner can navigate and exercise the full discussed workflow; core screens have meaningful data; changes appear in related views. Unresolved business decisions are visible for review.

## T03 — Workflow review and contracts

**Done:** the owner authorized autonomous delivery. Decisions are recorded in [EXECUTION.md](EXECUTION.md) instead of a review meeting.

Review the UI with the owner. Record accepted behavior, remaining changes, API shapes, and the role/agency permission matrix required for the next implementation. Mock assumptions must not silently become backend policy.

## T04 — Missing backend foundations

**Done:** settings, database sessions, health, Alembic migration, seed, Compose, and Dockerfile are implemented. SQLite verification passed; the PostgreSQL container path is unexecuted locally.

After workflow review, scope API/PostgreSQL Compose, settings, database sessions, health/readiness, and Alembic configuration/migrations as needed. Preserve working setup. Verify startup, disposable-database migrations, and persistence. Add no speculative domain tables or extra services.

## T05 — Real authentication

**Done:** cookie sessions, hashed tokens, CSRF/origin enforcement, password changes, logout, revocation, and frontend auth screens are connected and tested.

Define session lifecycle, CSRF protection, and permissions, then implement backend session operations and frontend integration. Verify logout/expiry, unauthenticated denial, wrong-role/record access, and agency isolation. Mock role switching must not affect real authorization.

## T06.<scope> — One feature migration

**Done:** candidate, staff, jobs/applications, and platform APIs are connected; runtime mocks were removed and the full workflow was smoke-tested. See repository CONTEXT files for evidence.

For each assigned feature:

1. Confirm its contract and dependencies; implement/test the real backend API.
2. Connect existing feature API functions/hooks without rebuilding the UI.
3. Verify the full workflow, errors, permissions, and Query invalidation.
4. Remove obsolete feature runtime mocks, fixtures, imports, registrations, and switches; search for dangling references. Keep unrelated mock features operational.

Never send mock-only IDs to real endpoints. Migrate dependent records together where necessary; name that related scope upfront. Isolated test fixtures may remain under tests, but must never reactivate runtime mock behavior.

**Done:** the feature uses the real API, its acceptance checks pass, runtime mock references are gone, and frontend/backend CONTEXT status is updated. No fallback to mocks on failure.
