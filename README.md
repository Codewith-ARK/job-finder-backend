# Job Finder — backend

FastAPI API with SQLAlchemy, Alembic, and Pydantic. Next.js supplies the views. Controllers call services; services query models directly.

**Status:** production prototype implemented and security-hardened. Real cookie sessions, CSRF protection, role/agency authorization, independent and referred candidate signup, resumable normalized onboarding, documents, staff assignment/team/job/referral operations, applications, and platform administration run against PostgreSQL in deployment and SQLite locally. Application rate limits, failed-login lockout, request-body caps, document quotas, ownership/eligibility guards, readiness, hardening headers, and a non-root container image are in place. Compose and the PostgreSQL path are authored but could not be executed on this workstation because Docker is not installed.

**Current priority:** verified local production prototype. Read [backend context](CONTEXT.md), [execution contract](docs/EXECUTION.md), and workspace `../AGENTS.md`.

## Run locally

From PowerShell, run these commands from the `backend` directory:

```powershell
uv sync
uv run alembic upgrade head
uv run seed
uv run fastapi dev main.py
```

The API will be available at `http://127.0.0.1:8000`. Stop the development
server with `Ctrl+C`. FastAPI's automatic API documentation is at
`http://127.0.0.1:8000/docs`. With `DOCS_TESTING_ENABLED=true` (the local
`.env` default), Swagger UI also accepts the API's own origin and echoes the
`jf_csrf` cookie on state-changing requests, so login and mutations can be
tested there. Keep that flag `false` outside local development.

| Item | Verified value |
| --- | --- |
| Python / tooling | Python `3.14.5`; `pyproject.toml` requires `>=3.14`; uv `0.12.9`; `uv.lock` and `.venv` present |
| Install | `uv sync` |
| Environment | Copy `.env.example` to `.env`; safe local defaults use SQLite at `data/jobfinder.db` |
| Migrations | `uv run alembic upgrade head` |
| Seed | `uv run seed` — idempotent; skips databases that already contain data |
| API start | `uv run fastapi dev main.py` (or `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`) |
| URLs | `http://127.0.0.1:8000`; liveness `GET /api/health`; readiness `GET /api/ready`; OpenAPI docs `/docs` |
| Checks | `uv run pytest -q` (74 passed); `uv run ruff check .` (clean) |

Demo accounts use password `Demo1234!` and the `@demo.example.com` domain:

| Role | Email |
| --- | --- |
| Candidate | `aya@demo.example.com` |
| Employee | `sam@demo.example.com` |
| Supervisor | `noor@demo.example.com` (Northstar and Harbor) |
| Platform admin | `jules@demo.example.com` |

Demo sign-in is disabled unless `DEMO_LOGIN_ENABLED=true`. The frontend `/demo` page performs real logins through `/api/auth/demo-login`; it is not a mock persona switcher.

## Environment

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL. Compose uses `postgresql+psycopg://...`; local default is `sqlite:///./data/jobfinder.db` |
| `APP_ENVIRONMENT` | `development`, `test`, or `production`; production refuses unsafe settings |
| `CORS_ORIGINS` | Comma-separated allowed browser origins, also enforced against `Origin` on state changes |
| `TRUSTED_HOSTS` | Comma-separated `Host` allowlist; empty disables host filtering |
| `HSTS_SECONDS` | HSTS max-age; `0` sends no header |
| `FORWARDED_ALLOW_IPS` | Proxy hops whose `X-Forwarded-For` is trusted (never `*`) |
| `DOCS_TESTING_ENABLED` | Local-only: allow the API's own origin and CSRF-echo in Swagger UI (`/docs`). Default `false` |
| `COOKIE_SECURE` | Set `true` behind HTTPS |
| `SESSION_DAYS` / `SESSION_RETENTION_DAYS` | Session lifetime and how long expired/revoked rows are kept |
| `DEMO_LOGIN_ENABLED` | Enables demo account sign-in and persona discovery |
| `SEED_ON_STARTUP` | Seeds an empty database at app startup |
| `MAX_UPLOAD_BYTES` / `MAX_DOCUMENTS_PER_CANDIDATE` / `MAX_CANDIDATE_DOCUMENT_BYTES` | Per-file size, per-candidate count, and aggregate storage quota |
| `REQUESTS_PER_MINUTE`, `AUTH_REQUESTS_PER_MINUTE`, `REGISTER_REQUESTS_PER_MINUTE` | Process-local per-IP limits |
| `LOGIN_MAX_FAILURES`, `LOGIN_LOCKOUT_SECONDS` | Per-account lockout after failed credentials |
| `MAX_WORKSPACE_ITEMS` | Hard row cap for workspace responses (no pagination contract yet) |

## Deployment

`compose.yaml` runs PostgreSQL 17 and the API in separate services with persistent database and document volumes. The API image runs `alembic upgrade head` before starting uvicorn, runs as an unprivileged user, and reports `/api/ready` through its healthcheck. PostgreSQL has no published port; the API publishes on `127.0.0.1:8000` only.

```bash
POSTGRES_PASSWORD=... CORS_ORIGINS=https://app.example.com docker compose up --build
```

Production uses the overlay, which requires every security-relevant value instead of falling back to a development default:

```bash
POSTGRES_PASSWORD=... CORS_ORIGINS=https://app.example.com \
TRUSTED_HOSTS=app.example.com HSTS_SECONDS=31536000 FORWARDED_ALLOW_IPS=172.18.0.1 \
docker compose -f compose.yaml -f compose.production.yaml up -d --build
```

For a local Compose run over plain HTTP, add `APP_ENVIRONMENT=development COOKIE_SECURE=false CORS_ORIGINS=http://localhost:3000`.

Topology: edge/CDN (TLS, WAF, per-IP limits) -> Next.js (`/api/*` rewrite) -> FastAPI on loopback. Run one API replica: the in-process request limiter is not shared. If replicas increase, move per-IP thresholds to the edge or a shared store; per-account login lockout and all authorization checks stay in the application either way. Set `FORWARDED_ALLOW_IPS` to the proxy address that actually reaches the API, never `*`.

PostgreSQL is the canonical deployment database. Local verification used the same models and migrations through SQLite because Docker/PostgreSQL were unavailable; the Postgres container path remains unexecuted here. Before first real traffic: run `uv run alembic upgrade head` and `GET /api/ready` against PostgreSQL, confirm the PostgreSQL-only migration findings (BUG-003/004/005 in `BUGS.md`), test a document upload/download through the volume, and verify HSTS and host filtering through the real proxy.

The API audits its effective configuration at startup and logs every risky or ambiguous setting
(origin whitespace or wildcards, docs testing, demo login, startup seeding, insecure cookies, long
sessions). A wildcard origin, production demo/seeding/docs, insecure cookies, non-HTTPS origins, or
default database credentials abort startup. See the hosting checklist in
[docs/EXECUTION.md](docs/EXECUTION.md#configuration-safety-and-hosting).

## API and permissions

All routes use the `/api` prefix and FastAPI's `{"detail": "..."}` error shape. The full contract is in [docs/EXECUTION.md](docs/EXECUTION.md).

- **Session:** opaque hashed token in HttpOnly `jf_session`; CSRF token mirrored in `jf_csrf` and required as `X-CSRF-Token` on state changes. Logout, password changes, and member deactivation revoke sessions.
- **Candidate:** independent account or single-use referral signup; own profile, preferences, experience, education, skills, and documents; ordered resumable onboarding; all open roles when independent or the referring agency's roles; one application per job.
- **Employee:** read agency candidates, teams, jobs, applications; update application status; create, list, and revoke own referral links.
- **Supervisor:** employee capabilities plus assignments, team member management, job writes, and every referral link in the active agency.
- **Platform admin:** platform overview, agencies, integrations, audit, and agency status; no agency workspace.
- Agency boundaries and record ownership are resolved server-side. Submitted role or agency IDs never grant access.

## Documentation and verification

Start with [START_HERE](docs/START_HERE.md), then [agent rules](AGENTS.md), [architecture](docs/ARCHITECTURE.md), [plan](docs/PLAN.md), and the [manual testing guide](docs/MANUAL_TESTING.md), and the [flow diagrams](docs/FLOWS.md).

For connection failures inspect configuration and service health; do not delete volumes as a troubleshooting shortcut. Run migrations against an empty database when schema changes are made, and never rewrite applied migrations.
