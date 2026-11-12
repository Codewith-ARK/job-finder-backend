# Plan — UI-first

**Decision confirmed:** visualize the complete application workflow with mock data first; connect real APIs feature by feature afterward. Architecture v0.2 remains approved. Assign a task or explicit sequence; this document does not start implementation automatically.

**Delivery status (12 November 2026):** T00–T06 complete. F01 is delivered and verified locally:
candidate independence, single-use agency referrals, and resumable normalized onboarding.
Remaining: owner manual acceptance, F02 when assigned, and deployment hardening (secure cookies,
disable demo sign-in and startup seeding).

## T00 — First-run inspection and local instructions

**Done. Scope:** read both repos; edit only README files, repository CONTEXT files, the Observed conventions sections of repository AGENTS files, and this task's status. Root fixed rules and application/configuration files stay unchanged.

Read root/scoped instructions first. Inspect manifests, lockfiles, actual folders, existing utilities, safe environment examples, and Git status. Verify available non-destructive startup/check commands. Do not install packages, regenerate lockfiles, edit secrets, or modify source code to complete the audit.

**Done:** READMEs contain verified commands or explicit unknowns; contexts distinguish existing from planned behavior; observed conventions are grounded in actual files; changes are documentation only. Report architectural conflicts and the next UI task, then stop.

## T01 — Frontend foundation for mock workflows

**Done. Scope:** frontend layouts, providers, shared UI, Query/Axios configuration, mock infrastructure, and relevant checks. Backend edits are excluded.

Create navigation and workspace shells, one stable QueryClient, and explicit development mock adapters behind feature API functions. Keep marketing independent. Use coherent shared mock state; keep feature-specific fixtures with their feature. No backend connection is required to demonstrate mock-only screens.

**Done:** navigation works; mock mode is visibly identified; relevant checks pass; UI does not issue unnecessary real requests.

## T02 — Complete the mock UI milestone

**Done:** T02.1–T02.4 completed the mock UI milestone, then the authorized T03–T06 sequence connected the real APIs.

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

## F01 — Candidate identity independence, referral links, and resumable onboarding

**Owner decision (12 November 2026):** full-stack delivery is authorized for this feature; the
UI-first preview step is explicitly waived. The backend contract governs the UI. Development
order is governed by [FEATURE_TRACKER.md](FEATURE_TRACKER.md); do not start F02 until F01 is
accepted.

**Status:** Done — 12 November 2026. See `FEATURE_TRACKER.md` for acceptance and evidence.

**Goal:** one integrated signup + onboarding flow for individual and agency-referred candidates.
Candidate profiles no longer require an agency. Referral links are single-use and expire.
Onboarding is resumable across logout/login and stores normalized profile data.

### F01.1 — Domain model and migration

- Make `candidate_profiles.agency_id` nullable; keep it as the referring agency while
  `memberships` remains the authorization source.
- Add personal/profile fields, and normalize professional and academic data into
  `candidate_preferences`, `candidate_experiences`, `candidate_education`, and
  `candidate_skills`.
- Add `referral_links` with a hashed token, expiry, single-use consumption, creator, agency, and
  revocation.
- Extend onboarding steps to `personal → professional → academic → documents`.
- Migrate existing preference/skill data without dropping populated databases.
- Update the seed with individual and referred candidates, normalized records, and referral
  fixtures.

### F01.2 — Backend APIs, authorization, and tests

- Registration accepts an optional referral token. Individual registration creates no
  membership; referral registration atomically consumes the token and creates membership +
  assignment to the referrer.
- Candidate sessions allow `agency = null`; staff sessions still require an active agency.
- Add referral resolve (public), create/list/revoke (staff) endpoints with CSRF and role checks.
- Add step-based onboarding save/complete endpoints with ordered transitions and validation.
- Update candidate workspace output, job visibility, application output, and staff directory
  queries for independent candidates.
- Tests: individual/referral signup, single-use/expiry/revocation, resumable onboarding,
  cross-agency denial, individual job visibility, staff isolation, migration up/down.

### F01.3 — Zustand store and unified wizard

- Add Zustand with persisted local draft state keyed by candidate, plus server autosave.
- Build the Account → Personal → Professional → Academic → Documents → Review wizard.
- Provide `/register`, `/join/[token]`, and resumable `/candidate/onboarding` entry points.
- Keep unsaved edits on refresh/logout; on login, restore saved server data and merge the local
  draft for the same user. Never store passwords or document files in local storage.

### F01.4 — Referral management and application integration

- Staff referral page with create, copy-once link, expiry, status, and revoke.
- Candidate onboarding gate; referral context shown at signup and in the candidate workspace.
- Individual candidate job browsing across active agencies; referred candidate agency jobs.
- Candidate/profile/application views updated for the expanded profile and job context.

### F01.5 — Verification and documentation

- Backend: `uv run ruff check .`, `uv run pytest -q`, migration upgrade/downgrade.
- Frontend: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, and end-to-end HTTP smoke
  for individual signup, referral signup, resume, completion, and staff referral management.
- Update `EXECUTION.md`, `FLOWS.md`, `MANUAL_TESTING.md`, `ARCHITECTURE.md`, both `CONTEXT.md`
  files, both observed-conventions sections, and `FEATURE_TRACKER.md`.

**Done:** all F01 acceptance criteria in `FEATURE_TRACKER.md` pass and F02 remains untouched.

## F03 — Security and deployment hardening

**Status:** Active — implementation and SQLite verification complete 13 November 2026;
PostgreSQL/container verification blocked. Governed by `FEATURE_TRACKER.md`; the findings and
per-item notes are in `BUGS.md`.

**Goal:** make the documented single-replica Compose deployment fail closed against the audit
findings without changing the application architecture or frontend contract.

### F03.1 — Configuration, throttling, and response hardening

- Add settings for trusted hosts, HSTS, login lockout, session retention, and workspace caps.
- Refuse unsafe production configuration at startup.
- Add per-IP limits, failed-login lockout with `Retry-After`, and session purge.
- Add `TrustedHostMiddleware`, HSTS, Permissions-Policy, CORP, CSP, `IntegrityError` → 409, and
  `GET /api/ready`.

### F03.2 — Authorization, onboarding, and document hardening

- Fail closed for suspended agencies and inactive referrers.
- Require complete onboarding before applying; invalidate steps when data is removed.
- Guard the last supervisor and multi-agency global role changes.
- Validate document structure, derive storage extensions from MIME type, enforce count/byte quotas,
  and compensate failed upload/delete operations.
- Reject blank required fields and cap tags, activity text, and workspace reads.

### F03.3 — Container, Compose, and indexes

- Run the image as an unprivileged user with a `/api/ready` healthcheck and trusted proxy hops.
- Keep PostgreSQL unpublished and the API loopback-only; add `compose.production.yaml` with
  required production values.
- Add additive migration `a7d2e5c91f04` for workspace/session indexes.

### F03.4 — Verification and documentation

- `uv run ruff check .`, `uv run pytest -q` (74 passed), migration upgrade/downgrade on disposable
  SQLite.
- Update `BUGS.md`, `CONTEXT.md`, `README.md`, `EXECUTION.md`, both observed-conventions sections,
  and `FEATURE_TRACKER.md`.

**Blocked:** PostgreSQL/Compose execution, populated-migration findings BUG-003/004/005, and edge
proxy settings. Do not mark F03 done until those run in a deployment-like environment.
