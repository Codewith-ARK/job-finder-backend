# Execution contract — production prototype

**Recorded:** 10 November 2026. Owner authorized autonomous delivery of the full workflow.
This document replaces T03 review assumptions with concrete decisions. Implementation follows
the approved v0.2 architecture; deviations are recorded here.

## Delivery target

A locally runnable production build with real persistence and authentication:

- FastAPI + SQLAlchemy + Alembic. **PostgreSQL is the canonical deployment database** and is
  wired through `compose.yaml` and `DATABASE_URL`.
- Docker/PostgreSQL are unavailable on the current workstation, so local verification uses the
  same SQLAlchemy models and Alembic migrations against **SQLite** (`DATABASE_URL` default).
  No forked code paths: only the connection URL and driver differ.
- Next.js production build served through `next start`, proxying `/api/*` to FastAPI.
- Seeded demo accounts are real database users; the demo chooser performs real logins.

## Identity and permissions

One user identity. Agency access comes from memberships. Roles are global:

| Role | Capabilities |
| --- | --- |
| `candidate` | Create an independent account or join through a single-use referral; read/update own profile, preferences, experiences, education, skills, documents; complete own onboarding in order; read all open roles when independent or the referring agency's roles when referred; apply once per job; read own applications. |
| `employee` | Read agency candidate directory, teams, jobs, applications; update application status; create/list/revoke own referral links. No assignments, team management, or job writes. |
| `supervisor` | Everything an employee can do, plus assign/reassign candidates, create/update/deactivate team members, create/update/close jobs, and list every referral link in the active agency. |
| `platform_admin` | Read platform overview, agencies, integrations, audit; update agency status. No agency workspace access. |

Rules:

- Identity, agency membership, and record ownership are resolved server-side from the session.
- Submitted role/agency IDs are never trusted as authorization.
- A candidate session may have `agency: null` (independent). Staff sessions always require an
  active agency membership; the session `agency` reflects the active membership.
- Platform admins have no agency; their session `agency` is `null`.
- Candidate data is visible to staff only within the same agency. Independent candidates have no
  membership, so they never appear in an agency directory.
- Referral signup creates the candidate, their agency membership, and their assignment to the
  referring employee/supervisor in one transaction, after consuming the single-use link.
- Deactivating a member revokes their sessions. A supervisor cannot deactivate themselves.

## Session and CSRF

- Opaque 256-bit session token stored **hashed** in `auth_sessions`; HttpOnly cookie `jf_session`,
  `Path=/`, `SameSite=Lax`, `Secure` when `COOKIE_SECURE=true`, 7-day expiry.
- CSRF token stored hashed with the session and mirrored in the non-HttpOnly `jf_csrf` cookie.
  Every cookie-authenticated state-changing request must send `X-CSRF-Token` matching it.
- Additionally, when an `Origin` header is present it must match `CORS_ORIGINS`.
  With `DOCS_TESTING_ENABLED=true` (local only), the API's own origin is also accepted and
  Swagger UI echoes the CSRF cookie, so `/docs` can exercise state-changing routes.
- Login/register/logout and demo login are state changes; they clear/rotate tokens.
- Sessions are revoked on logout, password change, and member deactivation.

**Decision: cookie sessions, not JWT.** Authentication uses an opaque, database-backed session
referenced by the HttpOnly `jf_session` cookie. No JWT is issued, no token is stored in
`localStorage`/`sessionStorage`, and the frontend never reads the session credential. This keeps
logout, password changes, and member deactivation able to revoke access immediately; a stateless
JWT would require a separate revocation list to match that behaviour.

## Configuration safety and hosting

Settings come from `config.py` (types, defaults, validation) and `.env` or the process environment
(overrides: environment > `.env` > code defaults). `get_settings()` is cached, so restart the API
after changing `.env`.

At startup `configuration_problems()` audits the effective configuration and logs every decision
that matters for hosting:

| Setting | Level | Effect |
| --- | --- | --- |
| `CORS_ORIGINS=*` | error | Refuses to start: the origin/CSRF allowlist would accept every site |
| Origin with whitespace, trailing `/`, invalid shape, duplicates, or empty entries | warning | Logs the trimmed/ignored interpretation |
| `DOCS_TESTING_ENABLED=true` | warning | Swagger UI accepts the API's own origin and echoes CSRF; local only |
| `DEMO_LOGIN_ENABLED=true` | warning | Demo persona sign-in is available |
| `SEED_ON_STARTUP=true` | warning | An empty database is seeded at startup |
| `COOKIE_SECURE=false` | warning | Session cookies may travel over plain HTTP |
| `SESSION_DAYS>30` | warning | Long-lived sessions |

The audit never silently "fixes" a risky setting: it logs the effective interpretation, and any
`error` entry aborts startup after the log line is written. Before hosting, set
`COOKIE_SECURE=true`, `DOCS_TESTING_ENABLED=false`, `DEMO_LOGIN_ENABLED=false`,
`SEED_ON_STARTUP=false`, and list explicit HTTPS origins. Keep `DOCS_TESTING_ENABLED=false` in
shared environments; `/docs` then rejects its own origin for state-changing calls.

## Domain model

`users`, `agencies`, `memberships` (user, agency, title, team, active), `auth_sessions`,
`candidate_profiles` (nullable `agency_id`), `candidate_preferences`, `candidate_experiences`,
`candidate_education`, `candidate_skills`, `onboarding_steps`, `documents`,
`referral_links`, `teams`, `candidate_assignments`, `jobs`, `applications`, `activities`,
`audit_events`, `integrations`.

- IDs are UUID strings. JSON columns are used for `job.tags` and platform integration payloads;
  candidate preferences, experience, education, and skills are normalized rows.
- Candidate stage: `onboarding | review | interview | ready`; assignment moves `onboarding` to `review`.
- Application status: `submitted | review | interview | offer | closed`; `next_step` is derived and
  the output includes the job title, company, and agency for candidate and staff views.
- Referral links store a hashed token, expiry, creator, agency, optional label, and `used_at` /
  `revoked_at`; the raw token is returned only once at creation.
- Activity/audit rows carry ISO `created_at`; the UI formats relative time.
- Documents are stored outside public/static paths and served only by an authorized endpoint.

## API contract (prefix `/api`)

All errors use FastAPI's `{"detail": "..."}` shape and stable HTTP status codes.

### Auth

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| GET | `/auth/session` | — | `Session \| null` |
| POST | `/auth/register` | `{name,email,password,referralToken?}` | `Session` (candidate; independent or referred) |
| POST | `/auth/login` | `{email,password,agencyId?}` | `Session` |
| POST | `/auth/demo-login` | `{personaId}` | `Session` (gated by `DEMO_LOGIN_ENABLED`) |
| GET | `/auth/demo-personas` | — | `DemoPersona[]` |
| POST | `/auth/context` | `{agencyId}` | `Session` |
| POST | `/auth/password` | `{currentPassword,newPassword}` | `204` |
| POST | `/auth/logout` | — | `204` |

`Session = { user: {id,name,email,role,label,workspace,agencies}, agency: Agency|null }`.

### Candidate

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| GET | `/candidates/me` | — | `{profile,preferences,experiences,education,skills,onboarding,nextSteps,documents,onboardingComplete,referral}` |
| PUT | `/candidates/me/onboarding/personal` | personal fields | Candidate workspace |
| PUT | `/candidates/me/onboarding/professional` | title, level, skills, experiences, preferences | Candidate workspace |
| PUT | `/candidates/me/onboarding/academic` | `{education: [...]}` | Candidate workspace |
| POST | `/candidates/me/onboarding/{stepId}/complete` | — | Candidate workspace |
| POST | `/candidates/me/documents` | multipart `file` | Candidate workspace |
| GET | `/candidates/me/documents/{id}` | — | file download |
| DELETE | `/candidates/me/documents/{id}` | — | Candidate workspace |

Onboarding order is `personal → professional → academic → documents`; completing a later step
first is `409`. Each step accepts partial saves, and completing it requires the step's minimum
fields. The documents step is completed by the final "finish onboarding" call, which also sets
`onboardingComplete` and the profile stage to `review`.

### Referrals

Public resolution never consumes a link. Creation returns the raw token once.

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| GET | `/referrals/{token}` | — | `{valid,status,agencyName,referrerName,label,expiresAt,reason}` |
| GET | `/referrals` | — | `ReferralLink[]` (employee: own; supervisor: agency) |
| POST | `/referrals` | `{label,expiresInDays}` | `{link,token,path}` |
| DELETE | `/referrals/{id}` | — | `ReferralLink[]` |

Used, expired, revoked, and unknown tokens resolve as invalid and are rejected at registration
with `409`.

### Staff

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| GET | `/staff/workspace` | — | `{stats,candidates,teamMembers,teams,activity}` |
| POST | `/staff/candidates/{candidateId}/assignment` | `{memberId\|null}` | Staff workspace |
| PATCH | `/staff/candidates/{candidateId}/stage` | `{stage}` | Staff workspace |
| POST | `/staff/members` | `{name,email,role,team}` | `{workspace, temporaryPassword}` |
| PATCH | `/staff/members/{memberId}` | `{role?,team?,active?}` | Staff workspace |

### Jobs

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| GET | `/jobs/workspace` | — | `{jobs,applications}` |
| POST | `/jobs` | `{title,company,location,workType,salary,tags,description}` | Jobs workspace |
| PATCH | `/jobs/{id}` | job fields and/or `status` | Jobs workspace |
| POST | `/jobs/{id}/apply` | — | Jobs workspace |
| PATCH | `/applications/{id}` | `{status}` | Jobs workspace |

### Platform

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| GET | `/platform/workspace` | — | `{stats,agencies,integrations,audit}` |
| PATCH | `/platform/agencies/{id}` | `{status}` | Platform workspace |

## Seed data

- Agencies: Northstar Careers (default), Harbor Talent, Meridian Group, Summit Talent.
- Demo users (password `Demo1234!`): Aya Khan (independent candidate), Sam Ali (employee),
  Noor Ahmed (supervisor, Northstar + Harbor), Jules Lee (platform admin).
- Candidate users: referred candidates with normalized preferences, experience, education, and
  skills, plus cross-agency data.
- Team members: Olivia Carter, Marcus Lee, Priya Shah, Daniel Kim.
- Jobs: Product Designer, Senior UX Researcher, Frontend Engineer, Product Manager.
- Referral fixtures: `northstar-referral-demo` (active, Sam Ali), `harbor-referral-used`,
  `northstar-referral-expired`; real PDF files back the seeded documents.
- Applications and activities seeded so every screen has meaningful populated state.
- Integrations are seeded with realistic statuses and labeled as simulated in the UI.

Seeding is idempotent and runs through a CLI command (`uv run seed`) or app startup when the
database is empty. Demo login is disabled unless `DEMO_LOGIN_ENABLED=true`.

## Frontend changes

- Remove mock adapters and `src/lib/mocks` for connected features; keep explicit empty/error/
  loading states. Never fall back to mocks after API failures.
- `http.client.ts`: `/api` base, credentials, cancellation, normalized `ApiError`, CSRF header
  interceptor; 401 clears private cache and redirects to `/login` (except session bootstrap).
- Auth: `/login`, `/register` (independent), `/join/[token]` (referral), `/demo` (real demo
  logins), agency switcher, password change, logout. Registration redirects to
  `/candidate/onboarding`. Route guards remain navigation only.
- Workspaces share a clean Flowbite-based app shell: sidebar, top bar, role-aware navigation.
- Candidate: dashboard, profile, resumable onboarding wizard (Account, Personal, Professional,
  Academic, Documents, Review), jobs, applications. A candidate layout gate sends incomplete
  candidates to onboarding.
- Staff: dashboard, candidates, team, jobs, applications, referral links (create, copy once,
  expiry, status, revoke).
- Platform: overview, agencies, integrations, audit.
- Mock-only presentation copy ("preview", "T02.x", "mock") is removed. External integrations
  remain visibly "Not connected".

## Verification

- Backend: 29 pytest checks covering auth (login/logout/expiry/CSRF), wrong-role and
  cross-agency denial, candidate ownership, onboarding order, individual/referral signup,
  single-use/expired/revoked referrals, normalized profile output, assignment/team/job/
  application flows, platform role, configuration audit, and migration up/down.
- Migrations run from empty DB; seed is idempotent.
- Frontend: Biome, typecheck, Node tests (draft merge/conversion/validation), production build
  (19 routes), and a 34-check HTTP smoke test against a fresh migrated database covering both
  signup paths, resume after logout/login, completion, job application, and referral management.
- No claim of a check that was not run.

## Out of scope

Email delivery, OAuth, payments, real third-party integrations, multi-tenant billing, and
background workers. Those surfaces stay clearly simulated or absent.
