# Architecture — approved v0.2

**Recorded:** 30 October 2026. Based on the approved [simple MVC proposal](https://chatgpt.com/library?file_id=libfile_ac740e8346588191b19ec497478314ed&account_id=505ed8a3-7fa5-45c2-adc4-c060fc724673). These are target boundaries; the real repositories still need inspection.

## Workspace

```text
project-name/
  frontend/    # Independent Git repository
  backend/     # Independent Git repository; owns shared documentation
```

The parent needs no Git repository. Its `AGENTS.md` supplies shared rules. Each repository owns `AGENTS.md`, `CONTEXT.md`, and README. Dashboards share one frontend and reusable features. **UI-first is confirmed:** mock workflows precede real feature integration.

## Frontend

```text
frontend/
  src/
    app/
      layout.tsx
      providers.tsx
      (marketing)/
      (auth)/
      (workspace)/
        candidate/
        staff/
        platform/
    features/
      auth/
      candidates/
      referrals/
      jobs/
        jobs.api.ts
        jobs.hooks.ts
        jobs.keys.ts
        jobs.types.ts
        components/
      applications/
      staff/
      teams/
    components/
      ui/
    lib/
      http.client.ts
      query.client.ts
  public/
  tests/
  .env.example
  next.config.ts
  package.json
  CONTEXT.md
  README.md
  AGENTS.md
```

Route groups contain real pages/layouts as needed. This map shows placement, not an instruction to generate empty features. Preserve the existing Next.js configuration extension if different.

Routes/layouts handle presentation composition. Feature hooks own remote-state behavior; feature API functions use the central Axios client. Shared components have no domain ownership. Mount the Query provider around auth/workspace routes, keeping marketing independent.

React Query retains its cache: configure freshness by resource, invalidate after writes, and clear private data on identity/agency changes. Browser queries are the initial dashboard approach; introduce server prefetching/hydration only for an identified screen requirement. See [TanStack Query defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults).

## Backend

```text
backend/
  src/app/
    __init__.py
    main.py
    config.py
    database.py
    security.py
    controllers/
      auth_controller.py
      jobs_controller.py
    services/
      auth_service.py
      jobs_service.py
    models/
      users_model.py
      jobs_model.py
    schemas/
      auth_schema.py
      jobs_schema.py
  alembic/
    env.py
    versions/
  tests/
  docs/
    ARCHITECTURE.md
    PLAN.md
    START_HERE.md
  .env.example
  .dockerignore
  Dockerfile
  compose.yaml
  pyproject.toml
  CONTEXT.md
  README.md
  AGENTS.md
```

Python package folders include `__init__.py`. Add other scopes using the same naming pattern only when needed. Tool configuration and lockfiles follow the inspected baseline.

| MVC role / concern | Owner |
| --- | --- |
| View | Next.js presentation |
| Controller | FastAPI controllers: HTTP handling and service calls |
| Model | SQLAlchemy entities and constraints |
| Business operations | Plain service functions: permissions, queries, transactions |
| API contracts | Pydantic schemas: validated input and explicit response fields |

Controllers never query the database. Services query models directly. No repository abstraction, generic base classes, or nested backend feature packages.

## Request and security boundaries

In explicit mock mode: component → hook → feature API → development mock adapter. For connected features: component → hook → feature API → Axios → FastAPI controller → service → model/database. Responses pass through explicit output schemas; [FastAPI documents their filtering behavior](https://fastapi.tiangolo.com/tutorial/response-model/).

Target one public origin: `/` serves Next.js and `/api/...` proxies to FastAPI. T00 records the existing mapping; foundation work establishes it if missing. Forward cookies correctly and document any prefix stripping. Avoid per-endpoint Next.js API wrappers.

**Deployment boundary (recorded 13 November 2026).** One API replica behind the Next.js `/api` rewrite, with an edge/CDN in front for TLS, WAF, and per-IP limits. FastAPI listens on loopback only; PostgreSQL has no published port. Uvicorn accepts forwarded client addresses only from `FORWARDED_ALLOW_IPS`, and `TRUSTED_HOSTS` restricts the `Host` header when configured. Application-level per-IP counters and failed-login lockout remain in force but are process-local: a second replica requires the same per-IP limits at the edge or a shared store. Do not add Nginx, Redis, or Kubernetes without a scoped requirement.

FastAPI validates sessions and authorizes agency, role, and record access. Host-only session cookies use `Path=/`, `HttpOnly`, a deliberate `SameSite` setting, and `Secure` under HTTPS. CSRF protection covers state-changing requests; cookie flags alone do not satisfy this rule. See [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

**Candidate identity and agency access.** A candidate is a user with a `candidate_profiles` row whose
`agency_id` may be `null`. Agency access is not implied by the profile column; it comes from an
active `memberships` row created by a referral signup or an assignment. Staff authorization always
resolves the active membership server-side, so independent candidates never appear in an agency
directory. Candidate profile data is normalized into `candidate_preferences`,
`candidate_experiences`, `candidate_education`, and `candidate_skills`; onboarding progress stays in
`onboarding_steps` with a fixed `personal → professional → academic → documents` order.

**Referral links.** `referral_links` stores a hashed single-use token with an expiry, creator,
agency, and optional revocation timestamp. Public resolution describes the link without consuming
it; registration consumes it atomically inside the same transaction that creates the user,
membership, profile, and assignment. The raw token is returned once at creation and never stored in
plaintext.

Next.js can read incoming cookies in Server Components using `await cookies()`; only cookies actually sent to its host/path are available. Reading a cookie does not validate a session. Any future authenticated server client must explicitly forward relevant credentials and avoid shared caching of private responses. See [Next.js cookies](https://nextjs.org/docs/app/api-reference/functions/cookies).

## Mocks and infrastructure

Explicit development-only mock adapters sit at each feature's API boundary and share its contracts. Keep adapters/fixtures under `features/<scope>/mocks/` and shared backing state under `src/lib/mocks/`, so cross-role screens reflect the same records. Components never embed fake datasets or silently replace failed API responses.

After UI review, implement real authentication, then migrate one scoped feature at a time. Keep its mock behavior until the real API and integration pass checks; then remove obsolete runtime mock data and references. Test fixtures may remain isolated under tests. Mixed modes must not send mock-only record IDs into real APIs.

Compose runs API and PostgreSQL separately. Persist database data; introduce a private upload volume with uploads. The API image runs migrations then uvicorn as an unprivileged user and healthchecks `/api/ready`. Add workers, shared object storage, or other services when a scoped feature requires them.
