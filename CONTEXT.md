# Backend context

**Current priority:** verified local production prototype. **Architecture:** approved simple MVC. Authentication, role/agency authorization, persistence, migrations, seed data, and all four domain APIs are implemented and tested. Docker/PostgreSQL deployment is authored but unexecuted locally.

## Responsibility

FastAPI will own identity, sessions, agency/role/record permissions, validated contracts, business rules, database operations, and private document access. Next.js supplies the views. Controllers call plain services; services query models directly.

Backend documentation preserves these boundaries during UI work. It does not instruct the agent to implement every backend feature immediately. Inspect and document the existing baseline now; retain it while the mock UI is developed.

## Planned sequence (completed)

1. Review the UI workflow and resolve relevant product/permission rules.
2. Establish missing database/Compose/migration foundations without replacing working setup.
3. Implement and verify real authentication and authorization first.
4. Implement one agreed feature API; connect its frontend and remove its obsolete runtime mocks after verification.

One identity system with agency memberships is fixed. Detailed role capabilities, onboarding transitions, session lifecycle, CSRF mechanism, and endpoint contracts must be recorded before their respective implementations. Mock screens are examples, not security policy.

## Evidence maintained by the agent

After T00, record actual runtime/tooling, implemented endpoints, database/migration status, and blockers here. During integration, list real features and their verification results. Do not confuse planned schemas or mock data with implemented API behavior. Keep setup commands in README and rules in AGENTS.

## T00 evidence

- The backend has one FastAPI app in `main.py` with only `GET /`; there are no controllers, services, models, schemas, auth/session handlers, database setup, migrations, or tests.
- No backend feature is API-connected. Authentication, authorization, agency membership, persistence, and private-document behavior remain planned contracts, not implemented behavior.
- `uv run fastapi dev main.py` started successfully and shut down cleanly; an in-process `GET /` health check returned `200`. PostgreSQL/Compose and migration verification are blocked by absent files and unavailable Docker.

## T03–T06 implementation evidence

- [docs/EXECUTION.md](docs/EXECUTION.md) records the approved role matrix, session/CSRF design, domain model, API paths, seed accounts, and verification scope. It supersedes the earlier review-only T03 assumption for this authorized delivery.
- **Structure:** `src/app/config.py`, `database.py`, `security.py`, `models/` (14 tables), `schemas/`, `services/`, `controllers/`, `main.py`, and `seed.py`. Controllers handle HTTP and delegate to plain services; services query models directly.
- **Authentication:** opaque 256-bit session tokens stored hashed, HttpOnly `jf_session` cookie, CSRF token stored hashed and mirrored in `jf_csrf`, `X-CSRF-Token` plus `Origin` enforcement on state changes, 7-day expiry, and session revocation on logout, password change, and member deactivation. Argon2 password hashes.
- **Authorization:** candidate ownership, agency membership boundaries, employee/supervisor/platform role checks, platform isolation from agency routes, and supervisor self-deactivation protection.
- **Persistence:** SQLAlchemy 2.x sync units of work, Alembic initial migration, and an idempotent seed for four agencies, demo accounts, candidates, teams, jobs, applications, activities, integrations, and audit events.
- **Documents:** validated PDF/DOC/DOCX uploads stored under a private configurable directory and downloadable only by the owning candidate.
- **Deployment:** `compose.yaml` (PostgreSQL 17 + API), `Dockerfile`, `.dockerignore`, and `.env.example`. The API container runs migrations before uvicorn.
- **Verified:** `uv run pytest -q` → 18 passed, covering login/logout, cookie clearing, password revocation, CSRF/origin denial, role and cross-agency access, onboarding order, assignment/team/job/application flows, document signature validation, and migration up/down. `uv run ruff check .` clean. Local API smoke-tested through the frontend proxy with seeded accounts.
- **Blocked:** Docker and PostgreSQL are unavailable on this workstation. The Compose/PostgreSQL path and container restart persistence have not been executed; SQLite uses the same models and migrations for local verification.
