# Job Finder — backend

FastAPI API with SQLAlchemy, Alembic, and Pydantic. Next.js supplies the views. Controllers call services; services query models directly.

**Status:** production prototype implemented. Real cookie sessions, CSRF protection, role/agency authorization, independent and referred candidate signup, resumable normalized onboarding, documents, staff assignment/team/job/referral operations, applications, and platform administration run against PostgreSQL in deployment and SQLite locally. Compose and the PostgreSQL path are authored but could not be executed on this workstation because Docker is not installed.

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
| URLs | `http://127.0.0.1:8000`; health `GET /api/health`; OpenAPI docs `/docs` |
| Checks | `uv run pytest -q` (29 passed); `uv run ruff check .` (clean) |

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
| `CORS_ORIGINS` | Comma-separated allowed browser origins, also enforced against `Origin` on state changes |
| `DOCS_TESTING_ENABLED` | Local-only: allow the API's own origin and CSRF-echo in Swagger UI (`/docs`). Default `false` |
| `COOKIE_SECURE` | Set `true` behind HTTPS |
| `SESSION_DAYS` | Session lifetime, default 7 days |
| `DEMO_LOGIN_ENABLED` | Enables demo account sign-in and persona discovery |
| `SEED_ON_STARTUP` | Seeds an empty database at app startup |
| `DOCUMENT_DIR` | Private document storage outside public paths, default `storage/documents` |

## Deployment

`compose.yaml` runs PostgreSQL 17 and the API in separate services with persistent database and document volumes. The API image runs `alembic upgrade head` before starting uvicorn.

```bash
docker compose up --build
```

PostgreSQL is the canonical deployment database. Local verification used the same models and migrations through SQLite because Docker/PostgreSQL were unavailable; the Postgres container path remains unexecuted here. Before any real deployment, set `COOKIE_SECURE=true` and disable demo sign-in and startup seeding.

The API audits its effective configuration at startup and logs every risky or ambiguous setting
(origin whitespace or wildcards, docs testing, demo login, startup seeding, insecure cookies, long
sessions). A wildcard origin aborts startup. See the hosting checklist in
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
