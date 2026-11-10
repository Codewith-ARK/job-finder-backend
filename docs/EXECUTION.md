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
| `candidate` | Read/update own profile, preferences, documents; complete own onboarding in order; read agency jobs; apply once per job; read own applications. |
| `employee` | Read agency candidate directory, teams, jobs, applications; update application status. No assignments, team management, or job writes. |
| `supervisor` | Everything an employee can do, plus assign/reassign candidates, create/update/deactivate team members, create/update/close jobs. |
| `platform_admin` | Read platform overview, agencies, integrations, audit; update agency status. No agency workspace access. |

Rules:

- Identity, agency membership, and record ownership are resolved server-side from the session.
- Submitted role/agency IDs are never trusted as authorization.
- Platform admins have no agency; their session `agency` is `null`.
- Candidate data is visible to staff only within the same agency.
- Deactivating a member revokes their sessions. A supervisor cannot deactivate themselves.

## Session and CSRF

- Opaque 256-bit session token stored **hashed** in `auth_sessions`; HttpOnly cookie `jf_session`,
  `Path=/`, `SameSite=Lax`, `Secure` when `COOKIE_SECURE=true`, 7-day expiry.
- CSRF token stored hashed with the session and mirrored in the non-HttpOnly `jf_csrf` cookie.
  Every cookie-authenticated state-changing request must send `X-CSRF-Token` matching it.
- Additionally, when an `Origin` header is present it must match `CORS_ORIGINS`.
- Login/register/logout and demo login are state changes; they clear/rotate tokens.
- Sessions are revoked on logout, password change, and member deactivation.

## Domain model

`users`, `agencies`, `memberships` (user, agency, title, team, active), `auth_sessions`,
`candidate_profiles`, `onboarding_steps`, `documents`, `teams`, `candidate_assignments`,
`jobs`, `applications`, `activities`, `audit_events`, `integrations`.

- IDs are UUID strings. JSON columns are used for `skills`, `job.tags`, and profile preferences.
- Candidate stage: `onboarding | review | interview | ready`; assignment moves `onboarding` to `review`.
- Application status: `submitted | review | interview | offer | closed`; `next_step` is derived.
- Activity/audit rows carry ISO `created_at`; the UI formats relative time.
- Documents are stored outside public/static paths and served only by an authorized endpoint.

## API contract (prefix `/api`)

All errors use FastAPI's `{"detail": "..."}` shape and stable HTTP status codes.

### Auth

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| GET | `/auth/session` | — | `Session \| null` |
| POST | `/auth/register` | `{name,email,password}` | `Session` (candidate, Northstar) |
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
| GET | `/candidates/me` | — | `{profile,onboarding,nextSteps,documents}` |
| PATCH | `/candidates/me/profile` | `{headline,location,skills}` | Candidate workspace |
| PATCH | `/candidates/me/preferences` | `{preferredWorkType,preferredLocation,salaryExpectation}` | Candidate workspace |
| POST | `/candidates/me/onboarding/{stepId}/complete` | — | Candidate workspace |
| POST | `/candidates/me/documents` | multipart `file` | Candidate workspace |
| GET | `/candidates/me/documents/{id}` | — | file download |
| DELETE | `/candidates/me/documents/{id}` | — | Candidate workspace |

Onboarding order is `profile → preferences → documents`; completing out of order is `409`.

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
- Demo users (password `Demo1234!`): Aya Khan (candidate), Sam Ali (employee), Noor Ahmed
  (supervisor, Northstar + Harbor), Jules Lee (platform admin).
- Candidate users: Ava Johnson, Liam Patel, Noah Kim, Emma Davis, plus cross-agency data.
- Team members: Olivia Carter, Marcus Lee, Priya Shah, Daniel Kim.
- Jobs: Product Designer, Senior UX Researcher, Frontend Engineer, Product Manager.
- Applications and activities seeded so every screen has meaningful populated state.
- Integrations are seeded with realistic statuses and labeled as simulated in the UI.

Seeding is idempotent and runs through a CLI command (`uv run seed`) or app startup when the
database is empty. Demo login is disabled unless `DEMO_LOGIN_ENABLED=true`.

## Frontend changes

- Remove mock adapters and `src/lib/mocks` for connected features; keep explicit empty/error/
  loading states. Never fall back to mocks after API failures.
- `http.client.ts`: `/api` base, credentials, cancellation, normalized `ApiError`, CSRF header
  interceptor; 401 clears private cache and redirects to `/login` (except session bootstrap).
- Auth: `/login`, `/register`, `/demo` (real demo logins), agency switcher, password change,
  logout. Route guards remain navigation only.
- Workspaces share a clean Flowbite-based app shell: sidebar, top bar, role-aware navigation.
- Candidate: dashboard, profile, onboarding (profile/preferences/documents), jobs, applications.
- Staff: dashboard, candidates, team, jobs, applications.
- Platform: overview, agencies, integrations, audit.
- Mock-only presentation copy ("preview", "T02.x", "mock") is removed. External integrations
  remain visibly "Not connected".

## Verification

- Backend: pytest covering auth (login/logout/expiry/CSRF), wrong-role and cross-agency denial,
  candidate ownership, onboarding order, assignment/team/job/application flows, platform role.
- Migrations run from empty DB; seed is idempotent.
- Frontend: Biome, typecheck, focused Node tests, production build; HTTP smoke test of every
  route with real login cookies.
- No claim of a check that was not run.

## Out of scope

Email delivery, OAuth, payments, real third-party integrations, multi-tenant billing, and
background workers. Those surfaces stay clearly simulated or absent.
