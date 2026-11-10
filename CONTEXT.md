# Backend context

**Current priority:** frontend workflow with mocks. **Architecture:** approved simple MVC. T00 verified a minimal FastAPI scaffold; backend feature implementation has not started.

## Responsibility

FastAPI will own identity, sessions, agency/role/record permissions, validated contracts, business rules, database operations, and private document access. Next.js supplies the views. Controllers call plain services; services query models directly.

Backend documentation preserves these boundaries during UI work. It does not instruct the agent to implement every backend feature immediately. Inspect and document the existing baseline now; retain it while the mock UI is developed.

## Later sequence

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
