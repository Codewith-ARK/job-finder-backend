# Backend agent rules

Applies to this repository. Read workspace `../AGENTS.md`, this file, `CONTEXT.md`, `README.md`, `docs/ARCHITECTURE.md`, the active feature in `docs/FEATURE_TRACKER.md`, and the assigned task in `docs/PLAN.md`. Architecture v0.2 is approved. **The UI-first milestone and initial real feature integration are complete; active work is governed by the feature tracker.**

## Scope

1. Complete only the assigned task or explicitly assigned task sequence. Name intended files first. Necessary controller/service/model/schema changes for one feature are allowed; unrelated refactors are excluded.
2. Preserve the working scaffold, Python tooling, lockfile, versions, and user changes. Do not re-scaffold, upgrade as cleanup, or alter the sibling frontend unless the task includes it.
3. Use FastAPI, Pydantic, SQLAlchemy, PostgreSQL, and Alembic. Install missing pieces only for a task that requires them. No repository layer, nested feature modules, generic CRUD base classes, or extra infrastructure without a scoped requirement.
4. Write efficient, DRY, modular, readable, functional code. Extract meaningful repetition without generic CRUD base classes.
5. Existing authorization covers the assigned work. Resolve material changes to product behavior, API contracts, dependencies, or architecture before expanding scope; do not ask again for an already approved task.

## Boundaries

| Location | Owns |
| --- | --- |
| `controllers/` | HTTP routing, validated inputs, authenticated context, service calls, response/status mapping. No SQL. |
| `services/` | Ordinary functions for business rules, record/agency permissions, queries, transactions. |
| `models/` | SQLAlchemy tables, relationships, constraints. |
| `schemas/` | Separate input/output contracts and allowed fields. |
| `main.py` | Application setup and router registration. |
| `config.py`, `database.py`, `security.py` | Settings, database connections/sessions, security helpers/dependencies. Auth dependencies delegate lookups to services. |

- Name by scope and singular concern: `jobs_controller.py`, `jobs_service.py`, `jobs_model.py`, `jobs_schema.py`. Python packages include `__init__.py`. Add files only when used.
- Services query models directly. Services never import controllers; models and schemas never import services/controllers. Keep service dependencies acyclic.
- Use request-scoped database sessions. The outer service operation owns commit/rollback; helpers must not commit partial workflows. Follow the existing sync/async database style consistently.
- Schema changes require reviewed Alembic migrations. Do not rewrite applied migrations, reset populated databases, or use runtime table creation instead of migrations.

## Security

- Resolve identity and verified agency membership server-side. Every private query/write must enforce applicable role and record ownership, including supplied relationship IDs. Never trust a submitted role or agency ID as authorization.
- Keep one user identity system with agency memberships. Role capabilities and onboarding transitions must be explicit in the assigned feature contract; unknown permissions deny access.
- Use explicit response schemas and allowlisted input fields. Never serialize password hashes, session credentials, provider tokens, or internal secrets. Keep SQL parameterized and sensitive values out of logs.
- Cookie sessions require backend validation, expiry/logout invalidation, suitable cookie flags, and a documented CSRF defense for state changes, including login/logout. Route guards and cookie presence are insufficient.
- Private documents remain outside public/static directories. Authorize downloads when that feature is implemented.

## Completion

Run configured checks and focused service/API tests. Changes to auth, permissions, or queries must test unauthenticated access, wrong role/record, and cross-agency denial. Exercise migrations against a disposable test database. Do not claim unrun checks passed.

Handoff: task ID; changed files; checks/results; migrations or contract changes; remaining blocker. Update the task status only when its acceptance criteria pass.

## UI-to-API handoff

Reviewed workflows and contracts guide implementation; mock role behavior is not authorization policy. Implement and verify real authentication first, then feature APIs. Coordinate removal of frontend runtime mocks only after the corresponding integration passes. Protect dependent record IDs during mixed mock/API development. Update CONTEXT with real endpoints and verified status.

## Observed conventions — agent maintained

- `pyproject.toml` requires Python `>=3.14`; `.python-version` contains `3.14`; `uv.lock` is present; uv `0.12.9` and Python `3.14.5` are installed with a local `.venv`.
- Application code lives in `src/app/`: `main.py` builds the FastAPI app, `config.py` uses pydantic-settings, `database.py` owns the engine/session/`Base`, and `models/`, `schemas/`, `services/`, `controllers/` follow the fixed MVC boundary. Root `main.py` only re-exports `app` for `fastapi dev main.py` and uvicorn.
- Runtime dependencies are FastAPI, SQLAlchemy 2.x, Alembic, psycopg, pwdlib/Argon2, python-multipart, and email-validator. Dev dependencies are pytest and ruff.
- `compose.yaml` runs PostgreSQL 17 and the API with persistent database/document volumes; the Dockerfile runs `alembic upgrade head` before uvicorn. Docker is not installed locally, so the PostgreSQL container path is unverified; local runs use SQLite through the same `DATABASE_URL` setting.
- Alembic has two reviewed migrations under `alembic/versions/`: the initial schema and `c4a9f1b2d7e8` (candidate independence, normalized profile tables, referral links). `uv run alembic upgrade head` applies both. `uv run seed` is idempotent and skips non-empty databases. Startup seeding is controlled by `SEED_ON_STARTUP`.
- Sessions use sync SQLAlchemy request-scoped sessions (`get_db`), with services owning commits. Domain failures raise `ServiceError` subclasses and are rendered as FastAPI `{"detail": ...}` responses by a global handler.
- Auth uses HttpOnly `jf_session`, mirrored `jf_csrf`/`X-CSRF-Token`, hashed opaque tokens, Argon2 passwords, and `Origin` checks on state changes. Role and agency authorization is resolved server-side; do not trust submitted role/agency IDs.
- Candidate access is independent by default: `candidate_profiles.agency_id` is nullable, agency visibility comes from an active `memberships` row, and only referred candidates appear in an agency directory. Registration accepts an optional referral token; referral links are single-use, expiring, and stored hashed.
- Onboarding is step-based (`personal → professional → academic → documents`) with partial saves and ordered completion. Preferences, experiences, education, and skills are normalized tables; `GET /candidates/me` returns the composed workspace.
- `config.py` owns settings, validation, and the startup `configuration_problems()` audit; `.env` supplies values and `get_settings()` is cached, so restart after edits. `CORS_ORIGINS=*` aborts startup, and `DOCS_TESTING_ENABLED=true` enables a CSRF-aware `/docs` interceptor for local testing only.
- Tests use `fastapi.testclient.TestClient` against the configured database plus a migration up/down test. Verified commands: `uv run pytest -q` (29 passed) and `uv run ruff check .` (clean). Run `uv run alembic upgrade head` before starting the API on a fresh database.
