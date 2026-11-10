# System and workflow diagrams

Mermaid diagrams for the implemented prototype. Render them in GitHub, GitLab, VS Code (Mermaid preview), or [mermaid.live](https://mermaid.live).

## 1. Runtime architecture

```mermaid
flowchart LR
  browser["Browser"]
  next["Next.js App Router<br/>React Query + Axios"]
  proxy["Next rewrite<br/>/api/* → API_ORIGIN"]
  api["FastAPI<br/>controllers"]
  services["Services<br/>rules, permissions, transactions"]
  db[("PostgreSQL<br/>or SQLite locally")]
  docs[("Private document<br/>storage")]

  browser -->|"HTTPS"| next
  next -->|"same-origin /api"| proxy
  proxy --> api
  api --> services
  services --> db
  services --> docs
```

## 2. Sign-in and CSRF sequence

```mermaid
sequenceDiagram
  autonumber
  actor User
  participant Web as Next.js
  participant API as FastAPI
  participant DB as Database

  User->>Web: Submit email + password
  Web->>API: POST /api/auth/login
  API->>DB: Verify Argon2 hash
  DB-->>API: User + memberships
  API->>DB: Store hashed session token + CSRF hash
  API-->>Web: Set-Cookie jf_session (HttpOnly), jf_csrf
  Web-->>User: Session JSON + redirect

  User->>Web: Change data (PATCH/POST)
  Web->>API: Cookie + X-CSRF-Token + Origin
  API->>API: Verify Origin, CSRF, role, agency, ownership
  API-->>Web: Updated resource
```

## 3. Candidate journey

```mermaid
flowchart TD
  start["Sign in at /demo or /login"] --> role{"Role is candidate?"}
  role -- "No" --> deny["403 or redirect to own workspace"]
  role -- "Yes" --> home["Candidate overview"]
  home --> done{"Onboarding complete?"}
  done -- "No" --> steps["Next step in order:<br/>profile → preferences → documents"]
  steps --> upload["Upload PDF or DOCX"]
  upload --> finish["Finish onboarding at 100%"]
  finish --> jobs["Browse agency jobs"]
  done -- "Yes" --> jobs
  jobs --> apply["Apply once per job"]
  apply --> submitted["Application: submitted"]
  submitted --> review["Under review"]
  review --> interview["Interview"]
  interview --> offer["Offer"]
  review --> closed["Closed"]
  interview --> closed
```

## 4. Staff and supervisor responsibilities

```mermaid
flowchart TD
  login["Staff sign in"] --> role{"Role"}
  role -- "Employee" --> read["Read agency candidates,<br/>teams, jobs, applications"]
  read --> status["Update application status"]
  role -- "Supervisor" --> tools["Supervisor tools"]
  tools --> assign["Assign or reassign candidates"]
  tools --> team["Create, update,<br/>deactivate team members"]
  tools --> jobswrite["Create, update, close jobs"]
  assign --> pipeline["Pipeline, counts, and activity update"]
  team --> pipeline
  jobswrite --> pipeline
  status --> pipeline
```

## 5. Request authorization decision

```mermaid
flowchart TD
  req["Private request"] --> session{"Valid session cookie?"}
  session -- "No" --> unauthorized["401 Unauthorized"]
  session -- "Yes" --> mutating{"State-changing request?"}
  mutating -- "Yes" --> csrf{"Valid Origin and<br/>X-CSRF-Token?"}
  csrf -- "No" --> forbidden["403 Forbidden"]
  csrf -- "Yes" --> role{"Required role?"}
  mutating -- "No" --> role
  role -- "No" --> forbidden
  role -- "Yes" --> scope{"Agency membership and<br/>record ownership valid?"}
  scope -- "No" --> forbidden
  scope -- "Yes" --> allow["Allow operation"]
```

## 6. Cross-role application update

```mermaid
sequenceDiagram
  autonumber
  actor C as Candidate
  participant API as FastAPI
  participant DB as Database
  actor S as Supervisor / Employee

  C->>API: POST /api/jobs/{jobId}/apply
  API->>DB: Insert application (submitted)
  API-->>C: Updated jobs workspace

  S->>API: GET /api/staff/workspace
  API-->>S: Candidate + application pipeline

  S->>API: PATCH /api/applications/{id} {status: interview}
  API->>DB: Update application + activity
  API-->>S: Updated staff workspace

  C->>API: GET /api/jobs/workspace
  API-->>C: Application now shows interview
```

## 7. Onboarding state

```mermaid
stateDiagram-v2
  [*] --> Profile
  Profile --> Preferences: complete profile
  Preferences --> Documents: complete preferences
  Documents --> Complete: upload document + finish
  Complete --> [*]
```

Completing a step out of order is rejected with `409`. Editing an already completed profile or preference step remains allowed.

## 8. Deployment

```mermaid
flowchart LR
  host["Browser"]
  web["Next.js<br/>next start"]
  api["FastAPI<br/>uvicorn :8000"]
  pg[("PostgreSQL 17")]
  vol[("documents volume")]

  host --> web
  web -->|"/api/*"| api
  api --> pg
  api --> vol
```

`compose.yaml` runs PostgreSQL and the API; the API container applies Alembic migrations before starting. The Docker/PostgreSQL path is authored but unexecuted on this workstation; local verification uses SQLite.
