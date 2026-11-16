| ID | Title | Severity | Category |
| --- | --- | --- | --- |
| BUG-001 | Team-member API can turn candidates into supervisors | High | Security |
| BUG-002 | Referred candidates can apply across agencies and receive foreign job data | High | Security |
| BUG-003 | PostgreSQL backfill inserts an integer into a boolean column | High | Data integrity |
| BUG-004 | Migrated completed candidates cannot reach the new academic step | High | Functional |
| BUG-005 | Downgrade silently deletes independent candidate profiles | High | Data integrity |
| BUG-006 | Authentication and registration have no abuse throttling | High | Security |
| BUG-007 | Compose defaults expose privileged demo access and a fixed-password database | High | Security |
| BUG-008 | Unauthenticated uploads are fully spooled before authorization and size checks | High | Security |
| BUG-009 | Applications bypass onboarding entirely | Medium | Functional |
| BUG-010 | Invalidated onboarding data still reports 100% complete | Medium | Data integrity |
| BUG-011 | Partial step saves erase omitted saved data | Medium | Data integrity |
| BUG-012 | Agency supervisors can change authority in other agencies | Medium | Architecture |
| BUG-013 | Deactivation counts the membership before its pending change is flushed | Medium | Security |
| BUG-014 | The last supervisor can demote themselves and strand agency administration | Medium | Functional |
| BUG-015 | Referral signup assigns candidates to inactive referrers | Medium | Data integrity |
| BUG-016 | Suspended-agency referral links resolve as valid | Medium | Functional |
| BUG-017 | Login to a suspended agency succeeds with an unusable session | Medium | Functional |
| BUG-018 | Concurrent duplicate registration and application return unhandled 500s | Medium | Data integrity |
| BUG-019 | Document filesystem and database writes can diverge on failure | Medium | Data integrity |
| BUG-020 | Four signature bytes are enough to pass document validation | Medium | Functional |
| BUG-021 | Unbounded upload filenames can produce filesystem errors | Medium | Functional |
| BUG-022 | Whitespace and empty strings bypass required-field validation | Medium | Functional |
| BUG-023 | Valid inputs generate activity text too long for PostgreSQL columns | Medium | Functional |
| BUG-024 | Job tag strings have no size bound | Medium | Performance |
| BUG-025 | Document storage has no per-user count or aggregate quota | Medium | Performance |
| BUG-026 | Workspaces and referral lists grow without pagination | Medium | Performance |
| BUG-027 | Staff and platform workspaces execute N+1 queries | Medium | Performance |
| BUG-028 | Tenant filters and session revocation lack supporting indexes | Medium | Performance |
| BUG-029 | Private responses lack explicit cache protection | Medium | Security |
| BUG-030 | Async upload handler runs blocking filesystem and database work | Medium | Performance |
| BUG-031 | Expired and revoked session rows have no cleanup policy | Medium | Architecture |
| BUG-032 | Repeated onboarding saves replace record IDs despite supplied IDs | Medium | Data integrity |
| BUG-033 | Non-ASCII CSRF headers raise an unhandled exception | Low | Functional |
| BUG-034 | Failed-login timing reveals whether an email exists | Low | Security |
| BUG-035 | Health endpoint provides no database readiness signal | Low | Architecture |
| BUG-036 | Direct API and docs responses omit browser hardening headers | Low | Security |
| BUG-037 | OpenAPI describes document downloads as JSON | Low | Architecture |

Audit date: **12 November 2026**, Asia/Karachi. **37 findings: 8 High, 24 Medium, 5 Low; no Critical finding established.**

## Remediation status — 13 November 2026

A follow-through pass closed every finding that can be verified without PostgreSQL, plus the deployment hardening the audit left undecided. Current status: **32 fixed**, **1 mitigated** (pagination, BUG-026), **1 not reproducible** (BUG-023), and **3 blocked** on a disposable PostgreSQL run (BUG-003/004/005).

- Verified locally: `uv run ruff check .` clean; `uv run pytest -q` -> 74 passed, including the hardening suite and an upgrade/downgrade migration test on disposable SQLite.
- Recorded topology decision: one API replica, edge/CDN -> Next.js `/api` rewrite -> FastAPI on loopback. Per-IP limits run in process; a second replica must move those limits to the edge or a shared store. The application still fails closed (account lockout, body caps, authorization) without the edge.
- Production startup refuses unsafe settings; see `compose.production.yaml`, `Dockerfile`, and `docs/EXECUTION.md#configuration-safety-and-hosting`.
- Deployment prerequisites, not verified here: run the migrations and readiness probe against PostgreSQL; confirm the backfill and downgrade findings BUG-003/004/005 there before importing real data; terminate TLS and add WAF/edge rate limits at the proxy; keep port 8000 off the public internet. Uploaded files are structurally validated, not malware-scanned.


## Scope, evidence, and safety

The audit began against the backend working tree, including uncommitted F01 referral/onboarding changes, above commit 229d27d. HEAD advanced during the audit to 0d1af6b (following implementation commit 84ce937). Final SHA-256 comparison confirmed that all 47 audited source, test, and migration files still matched the tested snapshot. Existing changes were preserved; the final Git status contained only untracked BUGS.md. The only file authored by this audit is this report; no fixes, dependency changes, commits, or feature-status changes were made by the audit.

All executable application tests used newly created SQLite databases under OS temporary directories, with DATABASE_URL, DOCUMENT_DIR, seeding, demo, cookie, origin, and session settings explicitly overridden **before app imports**. The audit never connected to the existing development database, a production database, or external application services. Synthetic accounts, seed rows, uploaded files, and temporary databases were removed afterward; all audit harnesses ran from stdin without creating script files. Failure injection used temporary in-process patches, not source edits.

Evidence labels in findings:

- **Observed:** reproduced through TestClient/ASGI or disposable-database operations.
- **Static / PostgreSQL unverified:** source-level defect or deployment risk; PostgreSQL execution was unavailable.
- **Injected failure:** reproduced with a controlled database/filesystem failure or latency; this establishes the failure path, not the normal production failure rate.
- **Design risk:** observed behavior whose broader product/deployment consequences require review.

The existing suite passed **29 tests in 40.95 seconds**. Ruff reported **All checks passed** using the existing executable with caching disabled. Additional tests included **115 anonymous/role checks**, **332 malformed-field/body requests**, 36 additional invalid-body cases, wrong-method checks on all 31 OpenAPI path entries, real signup/onboarding/staff/job/application/platform/referral flows, races, file handling, and bounded load tests. No production-capacity or long-duration stability claim is made.

Runtime: Python 3.14 environment; FastAPI 0.162.0, Starlette 1.10.0, SQLAlchemy 2.1.8, Pydantic 2.14.2, psycopg 3.3.8, python-multipart 0.0.32, pwdlib 0.3.1. The app uses opaque database-backed sessions, not JWT. There is no Celery, Redis, outbound URL fetcher, command execution endpoint, or external integration worker in the audited application.

## Intended flow and request conventions

Individual signup creates a candidate identity/profile without agency membership. Referral signup resolves a single-use link and atomically creates the identity, profile, membership, and referrer assignment. Both continue through personal → professional → academic → documents, preserving server progress across logout/login. Independent candidates browse active agencies' open jobs; referred candidates browse their own agency. Staff operate inside verified membership context; supervisors manage jobs, assignments, and team members. Platform admins manage agency status separately.

For every reproduction below:

- Use a disposable, migrated and seeded test database. Seed-only passwords are public fixture data: Demo1234!. Candidate: aya@demo.example.com; employee: sam@demo.example.com; supervisor: noor@demo.example.com; platform admin: jules@demo.example.com; Harbor supervisor: elena@harbor.example.com.
- Login with POST /api/auth/login and retain its cookies. Authenticated mutations send Origin: http://localhost:3000 and X-CSRF-Token equal to that client's jf_csrf cookie. A different origin is deliberately denied.
- IDs marked <candidate>, <member>, <job>, <application>, <agency>, or <link> are taken from the preceding response/workspace, not guessed. User/member/candidate IDs are user IDs; the membership row has its own internal ID.
- API fields are camelCase. Unknown input keys are ignored; tested role/agency/password-hash mass-assignment keys on registration did not grant privileges.
- Unless specified, successful operations return 200; password change/logout return 204. Expected domain errors use an object with detail text, while validation errors use detail arrays. Observed unhandled 500s instead return plain Internal Server Error.

## Complete route inventory and coverage

Roles: C = candidate, E = employee, S = supervisor, P = platform admin. “Session” means a valid active session; applicable agency membership/status is checked server-side. “CSRF” includes the mirrored cookie/header validation; the global origin guard also applies to mutations. Request names and response shapes are expanded below. Every listed API operation was exercised; failures/findings qualify the coverage.

| Method | Path | Authentication / roles | Request | Response | Executed flow / negative coverage |
| --- | --- | --- | --- | --- | --- |
| GET | /api/health | Public | None | {status:string} | 200; DB-failure simulation; wrong method |
| GET | /api/auth/session | Public; resolves optional cookie | None | Session or null | All roles; missing, forged, expired, revoked cookie |
| GET | /api/auth/demo-personas | Public; DEMO_LOGIN_ENABLED gate | None | DemoPersona[] | Discovery; disabled-gate denial; wrong method |
| POST | /api/auth/register | Public; origin guard | Register | Session + cookies | Individual/referral; duplicate; malformed; concurrent; role injection |
| POST | /api/auth/login | Public; origin guard | Login | Session + cookies | All roles; bad password; invalid agency; suspended agency; burst |
| POST | /api/auth/demo-login | Public; demo gate + origin guard | {personaId:string} | Session + cookies | Seed persona; invalid IDs/types; origin denial |
| POST | /api/auth/context | Session, CSRF; membership required | {agencyId:string} | Session | Northstar ↔ Harbor; unauthorized/missing agency; malformed |
| POST | /api/auth/password | Session, CSRF; all roles | {currentPassword,newPassword} | 204 + cleared cookies | Wrong password; successful change; stale session replay; invalid fields |
| POST | /api/auth/logout | Session, CSRF; all roles | None | 204 + cleared cookies | Revocation; cookie clearing; repeated login/logout; CSRF denial |
| GET | /api/candidates/me | Session, C | None | CandidateWorkspace | Own data; anonymous/wrong roles; resume after login |
| PUT | /api/candidates/me/onboarding/personal | Session, C, CSRF | Personal | CandidateWorkspace | Save/complete prerequisite; partial/empty/null/oversize; URL probes |
| PUT | /api/candidates/me/onboarding/professional | Session, C, CSRF | Professional | CandidateWorkspace | Save; order; skills/experience; replacement IDs; malformed |
| PUT | /api/candidates/me/onboarding/academic | Session, C, CSRF | Academic | CandidateWorkspace | Save; order; empty/blank data; malformed dates/years |
| POST | /api/candidates/me/onboarding/{step_id}/complete | Session, C, CSRF | Path step; no body | CandidateWorkspace | All four steps; early/missing/repeated steps; stale completion |
| POST | /api/candidates/me/documents | Session, C, CSRF, after multipart parsing | Multipart file | CandidateWorkspace | Upload; missing/invalid/oversize; filename; unauth spool; fault injection |
| GET | /api/candidates/me/documents/{document_id} | Session, owning C | Document ID | File bytes | Download; ownership; nonexistent row/file; Range 206/416 |
| DELETE | /api/candidates/me/documents/{document_id} | Session, owning C, CSRF | Document ID | CandidateWorkspace | Delete; ownership; nonexistent ID; disk failure; completion |
| GET | /api/staff/workspace | Session, E/S | None | StaffWorkspace | Tenant directory/team/activity; role matrix; query/load measurements |
| POST | /api/staff/candidates/{candidate_id}/assignment | Session, S, CSRF | {memberId:string or null} | StaffWorkspace | Assign/reassign/unassign; wrong role/agency/member; invalid IDs |
| PATCH | /api/staff/candidates/{candidate_id}/stage | Session, S, CSRF | {stage} | StaffWorkspace | Stage changes; wrong role/agency; invalid enum/body |
| POST | /api/staff/members | Session, S, CSRF | MemberCreate | {workspace,temporaryPassword} | Create; login using returned password; duplicates; invalid role/fields |
| PATCH | /api/staff/members/{member_id} | Session, S, CSRF | MemberPatch | StaffWorkspace | Team/role/active; candidate target; self/other agency; revocation |
| GET | /api/jobs/workspace | Session, C/E/S | None | JobsWorkspace | Candidate visibility; agency staff; platform denial; bulk/query tests |
| POST | /api/jobs | Session, S, CSRF | Job | JobsWorkspace | Create; wrong role; whitespace; huge tags; invalid fields |
| PATCH | /api/jobs/{job_id} | Session, S, CSRF | JobPatch | JobsWorkspace | Update/close/reopen; wrong agency; empty/null/invalid fields |
| POST | /api/jobs/{job_id}/apply | Session, C, CSRF | Job ID; no body | JobsWorkspace | Apply; duplicate/closed/missing; cross-agency; incomplete profile; race |
| PATCH | /api/applications/{application_id} | Session, E/S, CSRF | {status} | JobsWorkspace | Status read-back by candidate; wrong role/agency; invalid enum/ID |
| GET | /api/referrals/{token} | Public | Token path | ReferralResolve | Active/unknown/used/expired/revoked/suspended-agency links |
| GET | /api/referrals | Session, E/S | None | ReferralLink[] | Employee own links; supervisor agency list; tenant/role denial |
| POST | /api/referrals | Session, E/S, CSRF | {label?,expiresInDays?} | {link,token,path} | Create/resolve/signup; bounds/null/type probes; role denial |
| DELETE | /api/referrals/{link_id} | Session, E/S, CSRF | Link ID | ReferralLink[] | Revoke; repeated/reused/cross-employee/cross-agency denial |
| GET | /api/platform/workspace | Session, P | None | PlatformWorkspace | Overview; wrong-role isolation; query/load measurements |
| PATCH | /api/platform/agencies/{agency_id} | Session, P, CSRF | {status} | PlatformWorkspace | Suspend/reactivate; audit read-back; wrong role/ID/enum |

Supplemental framework surfaces: GET/HEAD /openapi.json, /docs, and /docs/oauth2-redirect returned 200 with normal docs configuration. With DOCS_TESTING_ENABLED=true, the app substitutes its custom GET /docs CSRF-aware page; the existing suite exercised its interceptor and own-origin toggle. /redoc and / returned 404. TRACE on every OpenAPI path entry returned 405. These documentation surfaces are public by implementation.

### Request and response shapes

A question mark means optional; array maximums and string limits live in src/app/schemas/. Output arrays currently have no pagination.

- Register: {name:string(1..120),email:email,password:string(8..128),referralToken?:string|null}.
- Login: {email:email,password:string(1..128),agencyId?:string|null}.
- Session: {user:{id,name,email,role,label,workspace,agencies:[{id,name}]},agency:{id,name}|null}.
- DemoPersona: {id,name,role,label,description,workspace}.
- Personal: {phone?,location?,headline?,summary?,linkedinUrl?,portfolioUrl?}; all are strings defaulting to empty.
- Professional: {currentTitle?,experienceLevel,skills?:string[],experiences?:Experience[],preferences:Preference}. Experience: {id?,company,title,location?,startDate:YYYY-MM,endDate?:YYYY-MM|null,current?:boolean,description?}. Preference: {workType,preferredLocation?,salaryExpectation?,availability?,willingToRelocate?:boolean}. Experience levels: Entry/Junior/Mid/Senior/Lead/Executive. Preference work types also permit Flexible.
- Academic: {education?:Education[]}. Education: {id?,institution,degree,fieldOfStudy?,startYear:1950..2100,endYear?:1950..2100|null,grade?}; end must not precede start.
- CandidateWorkspace: {profile:{name,email,headline,summary,phone,location,linkedinUrl,portfolioUrl,currentTitle,experienceLevel,completion,stage},preferences:Preference|null,experiences:[Experience with id],education:[Education with id],skills:string[],onboarding:[{id,title,description,status}],nextSteps:string[],documents:[{id,filename,size,createdAt}],onboardingComplete:boolean,referral:{agencyName,referrerName,label}|null}.
- MemberCreate: {name,email,role:employee|supervisor,team}; MemberPatch: {role?,team?,active?:boolean|null}. Candidate stages: onboarding/review/interview/ready.
- StaffWorkspace: {stats:{activeCandidates,openAssignments,onboardingInProgress,applicationActivity},candidates:[{id,name,headline,location,status,onboarding,assignedTo,skills,updatedAt}],teamMembers:[{id,name,email,role,team,workload,active}],teams:string[],activity:[{id,title,detail,tone,createdAt}]}.
- Job: {title,company,location,workType:Remote|Hybrid|On-site,salary,tags?:string[],description?}. JobPatch permits optional/nullable job fields plus status:open|closed; null values are ignored.
- JobsWorkspace: {jobs:[{id,agencyName,title,company,location,workType,salary,tags,status,posted,description}],applications:[{id,jobId,jobTitle,company,agencyName,candidateId,candidateName,status,submittedAt,nextStep,updatedAt}]}.
- Application status: submitted/review/interview/offer/closed.
- ReferralCreate: {label?:string(0..120),expiresInDays?:integer(1..30)}. ReferralLink: {id,label,tokenHint,agencyName,createdByName,status,expiresAt,createdAt,usedAt,revokedAt}. ReferralResolve: {valid,status,agencyName,referrerName,label,expiresAt,reason}; invalid links deliberately return 200 with valid:false. Create additionally returns the raw token and /join/<token> path once.
- PlatformWorkspace: {stats:{agencies,users,integrations,health},agencies:[{id,name,region,users,status,integrations}],integrations:[{id,name,type,status,lastSync}],audit:[{id,event,detail,actor,createdAt}]}. Agency status: active/pending/suspended.

## Findings

### [BUG-001] Team-member API can turn candidates into supervisors

- **Status:** Fixed
- **What changed:** src/app/services/staff_service.py; tests/test_audit_fixes.py
- **Test added:** test_candidate_cannot_be_managed_as_staff
- **Notes:** Reproduced 200 privilege escalation before fix; replay now denies candidate targets with 403. Security correction changes previously unauthorized success to existing Forbidden response.

- **Category:** Security
- **Severity:** High
- **Location:** PATCH /api/staff/members/{member_id}; src/app/services/staff_service.py:355-369.
- **What's wrong:** Observed: a supervisor can target a candidate's membership with the team-member endpoint and change that identity into a supervisor. The candidate's existing cookie immediately gains the staff workspace.
- **How to reproduce:** Register a candidate using a fresh Northstar referral. As Noor, PATCH /api/staff/members/<candidate user ID> with {"role":"supervisor"}. It returns 200; the candidate's GET /api/auth/session now reports supervisor and GET /api/staff/workspace returns 200.
- **Probable cause:** The lookup accepts every agency membership and excludes only platform_admin targets; it never requires the target to already be employee/supervisor.
- **Suggested fix direction:** Restrict team-management targets to authorized staff identities. Any candidate-to-staff conversion needs its own explicit lifecycle and permission contract.

### [BUG-002] Referred candidates can apply across agencies and receive foreign job data

- **Status:** Fixed
- **What changed:** src/app/services/jobs_service.py; src/app/controllers/jobs_controller.py; tests/test_audit_jobs.py
- **Test added:** test_referred_application_respects_agency; test_independent_application_preserves_workspace_scope
- **Notes:** Both failed before fix, replayed in the 32-passing safe suite. Foreign referred applications now use existing 404 denial; independent mutation response retains all allowed agencies. Client-visible security correction flagged below.

- **Category:** Security
- **Severity:** High
- **Location:** POST /api/jobs/{job_id}/apply; src/app/services/jobs_service.py:158-190.
- **What's wrong:** Observed: a Northstar-referred candidate can submit an application to Harbor by supplying its job ID. The mutation response also returns Harbor's open jobs despite the candidate's Northstar-only browsing context.
- **How to reproduce:** Obtain Content Designer's ID using an independent candidate's GET /api/jobs/workspace. Register another candidate with a Northstar referral; its normal workspace contains only Northstar jobs. POST /api/jobs/<Harbor job>/apply with that referred client's CSRF header: 200, a Harbor application, and Harbor jobs in the response.
- **Probable cause:** apply_to_job checks job/agency status and duplicates but never checks the candidate's membership/context. It renders the response using job.agency_id.
- **Suggested fix direction:** Enforce the intended independent/referred visibility policy before insertion, and render the response using the authenticated candidate's allowed scope.

### [BUG-003] PostgreSQL backfill inserts an integer into a boolean column

- **Status:** Blocked: needs PostgreSQL verification
- **What changed:** No implementation change for this finding.
- **Test added:** None; not closed.
- **Notes:** Deployment prerequisite: Docker and PostgreSQL are unavailable on this workstation. Verification blocked, not a false-positive determination. PostgreSQL is unavailable; integer/boolean failure cannot be re-run. Existing migration is applied history: choose a reviewed release/repair strategy rather than editing it blindly. Recommend disposable PostgreSQL verification before any deployment.

- **Category:** Data integrity
- **Severity:** High
- **Location:** Alembic upgrade c4a9f1b2d7e8; alembic/versions/c4a9f1b2d7e8_candidate_independence_referrals.py:37-38,198-211.
- **What's wrong:** Static / PostgreSQL unverified: the populated-database backfill inserts literal integer 0 into boolean willing_to_relocate. PostgreSQL rejects an integer expression in a boolean assignment, so existing-profile upgrades are expected to fail; SQLite tests mask this.
- **How to reproduce:** On a disposable PostgreSQL database, migrate to 83f1a1cd3f41, create one legacy candidate profile, then upgrade head. The generated INSERT contains VALUES (..., '', 0, :now). The minimal type check is CREATE TEMP TABLE boolean_probe(value boolean); INSERT INTO boolean_probe VALUES (0);. PostgreSQL execution was not available here.
- **Probable cause:** A SQLite-compatible raw SQL literal was used in a migration targeting both engines. PostgreSQL distinguishes numeric expressions from boolean literals; see the [PostgreSQL explanation and reproducer](https://www.postgresql.org/message-id/CAKFQuwZXYgDxDLkB4a2jVn%2BbcuyxEWyROoKL8z-fwfrbS1pFgA%40mail.gmail.com).
- **Suggested fix direction:** Use a correctly typed boolean expression/bind and test populated upgrades against PostgreSQL.

### [BUG-004] Migrated completed candidates cannot reach the new academic step

- **Status:** Blocked: needs PostgreSQL verification
- **What changed:** No implementation change for this finding.
- **Test added:** None; not closed.
- **Notes:** Deployment prerequisite: Docker and PostgreSQL are unavailable on this workstation. Verification blocked, not a false-positive determination. Reproduction requires executing the existing data-altering migration, prohibited for this task. Recommend a reviewed forward-only repair migration; choose whether legacy completion is grandfathered or revalidated.

- **Category:** Functional
- **Severity:** High
- **Location:** Candidate onboarding save/complete routes; alembic/versions/c4a9f1b2d7e8_candidate_independence_referrals.py:300-351; src/app/services/candidates_service.py:243-249,384-396.
- **What's wrong:** Observed on a populated legacy database: candidates who completed all old steps migrate to personal=complete, professional=complete, academic=upcoming, documents=complete. Completion becomes 75%, with no next step and no supported way to enter academic.
- **How to reproduce:** At revision 83f1a1cd3f41, insert a candidate with profile/preferences/documents all complete. Upgrade head. Read the workspace, then save or complete academic: Conflict, “Complete the current onboarding step first.” Re-completing an already completed step returns early and does not advance it.
- **Probable cause:** Migration makes academic next only when the old documents step was next, not when it was complete.
- **Suggested fix direction:** Recalculate the first incomplete step for every migrated state and validate required content rather than blindly preserving completed flags.

### [BUG-005] Downgrade silently deletes independent candidate profiles

- **Status:** Blocked: needs PostgreSQL verification
- **What changed:** No implementation change for this finding.
- **Test added:** None; not closed.
- **Notes:** Deployment prerequisite: Docker and PostgreSQL are unavailable on this workstation. Verification blocked, not a false-positive determination. Destructive downgrade reproduction is expressly prohibited. Do not interpret this as a false positive. Recommend a guard refusing incompatible downgrade; backup/export and rollback policy need approval.

- **Category:** Data integrity
- **Severity:** High
- **Location:** Alembic downgrade to 83f1a1cd3f41; alembic/versions/c4a9f1b2d7e8_candidate_independence_referrals.py:534-555.
- **What's wrong:** Observed: downgrade deletes every profile with agency_id IS NULL while leaving its user identity. It also drops the new normalized/referral tables. This is an intentional, documented conversion choice, but execution has no populated-data guard or export requirement.
- **How to reproduce:** In a disposable head database, register an independent candidate, then run alembic downgrade 83f1a1cd3f41. The profile count for that ID changes from 1 to 0; its users row remains. The normal candidate workspace can no longer load after returning to head without reconstructing the lost profile.
- **Probable cause:** The older schema cannot represent independent candidates, and the migration resolves this by deleting them automatically.
- **Suggested fix direction:** Refuse destructive downgrade when incompatible data exists unless an explicit backup/export and approved conversion policy are supplied.

### [BUG-006] Authentication and registration have no abuse throttling

- **Status:** Fixed
- **What changed:** src/app/config.py; src/app/request_guards.py; src/app/throttle.py; src/app/services/auth_service.py; src/app/services/errors.py; src/app/main.py
- **Test added:** tests/test_request_guards.py::test_login_attempts_are_limited; tests/test_production_hardening.py::test_failed_logins_lock_the_account_without_breaking_successful_ones
- **Notes:** Per-IP limits bound every API path, with a tighter budget for auth and registration. Per-account lockout counts only failed credentials and resets on a successful sign-in, so ordinary successful traffic never locks an account; repeated failures return 429 with Retry-After. A deliberate attacker can still force a temporary lockout for a known account, which is the accepted cost of failure-based lockout and is bounded by the per-IP limit. Limits remain process-local and assume one API replica: a second replica requires the same limits at the deployed edge. Thresholds are configuration values (LOGIN_MAX_FAILURES, LOGIN_LOCKOUT_SECONDS, *_REQUESTS_PER_MINUTE) and can still be tuned after client review.

- **Category:** Security
- **Severity:** High
- **Location:** POST /api/auth/login, /register, /demo-login, /password; src/app/controllers/auth_controller.py:41-91; src/app/services/auth_service.py:165-223.
- **What's wrong:** Observed and source-reviewed: there is no application-level rate limit, backoff, lockout, or session-creation cap. An anonymous caller can repeatedly trigger Argon2 work or register new accounts.
- **How to reproduce:** Send 32 bad-password requests for sam@demo.example.com with eight concurrent local clients. All 32 returned 401, none 429, with median 333.12 ms and p95 392.73 ms. Repeat registration with unique synthetic emails to create additional users/sessions.
- **Probable cause:** Public authentication routes directly perform database/password operations without abuse controls; no gateway rate-limit configuration is supplied.
- **Suggested fix direction:** Add bounded per-source and per-account controls at the deployed boundary, including registration and expensive password operations. No brute-force cracking or host exhaustion was attempted.

### [BUG-007] Compose defaults expose privileged demo access and a fixed-password database

- **Status:** Fixed
- **What changed:** src/app/config.py; compose.yaml; compose.production.yaml; Dockerfile; .env.example
- **Test added:** tests/test_config.py; tests/test_production_security.py::test_production_rejects_unsafe_configuration
- **Notes:** Production refuses demo login, startup seeding, docs testing, insecure cookies, non-HTTPS origins, development database credentials, and out-of-range session lifetimes. PostgreSQL has no published port; the API publishes on loopback only. compose.production.yaml requires the public origin, host allowlist, HSTS max-age, and trusted proxy hop. Demo accounts remain available only when explicitly enabled locally.

- **Category:** Security
- **Severity:** High
- **Location:** Deployment of /api/auth/demo-personas and /demo-login; compose.yaml:4-16,20-36; src/app/config.py:23-28; src/app/seed.py:32-36,201-205.
- **What's wrong:** Static deployment risk: the supplied Compose defaults enable demo login/startup seeding, use non-Secure cookies, and publish PostgreSQL on all host interfaces with a fixed development password. The seeded platform administrator is accessible through the demo chooser; disabling only demo-login still leaves normal login to seeded public-password accounts.
- **How to reproduce:** Review the defaults used by docker compose up without overrides. In an isolated seeded API with DEMO_LOGIN_ENABLED=true, GET /api/auth/demo-personas, select the platform persona, and POST /api/auth/demo-login with its personaId: a real privileged session is issued without a password.
- **Probable cause:** The template intentionally targets a demo deployment; startup warnings and README instructions are the only protection against reusing it for real data.
- **Suggested fix direction:** Provide explicit development-only opt-in and a deployment configuration that refuses seeded/demo privileged access, requires secure transport, and keeps the database private. No real deployment or production configuration was inspected.

### [BUG-008] Unauthenticated uploads are fully spooled before authorization and size checks

- **Status:** Fixed
- **What changed:** src/app/request_guards.py; src/app/security.py
- **Test added:** tests/test_request_guards.py::test_unauthorized_upload_body_is_not_read; ::test_forged_upload_session_is_denied_before_parsing; ::test_chunked_body_limit_without_content_length
- **Notes:** The guard authenticates the upload and checks content length before multipart parsing, caps the streamed body, times out slow uploads, and limits concurrent readers. Client addresses must be validated by the ASGI server's proxy policy; the container trusts only FORWARDED_ALLOW_IPS.

- **Category:** Security
- **Severity:** High
- **Location:** POST /api/candidates/me/documents; src/app/controllers/candidates_controller.py:65-77; src/app/main.py:109-113.
- **What's wrong:** Observed: an unauthenticated upload larger than the configured maximum was fully written to the multipart spool before returning 401. The endpoint's 10 MB read/check happens after the framework has consumed multipart file data, and there is no early total-body cap.
- **How to reproduce:** Without cookies, POST multipart file too-big.pdf containing b"%PDF" + b"x" * (11 * 1024 * 1024). Instrument tempfile.SpooledTemporaryFile.write in-process: **11,534,340 bytes** are written before 401, despite MAX_UPLOAD_BYTES=10,485,760. A signed-in oversized request returns 409 only after parsing.
- **Probable cause:** FastAPI resolves File(...) by parsing multipart before dependency authorization, while the limit is enforced in the controller/service afterward.
- **Suggested fix direction:** Enforce a streaming total-body limit before multipart parsing, including chunked requests, and reject unauthorized upload traffic early. Tests stopped at 11 MB; disk exhaustion was not attempted.

### [BUG-009] Applications bypass onboarding entirely

- **Status:** Fixed
- **What changed:** src/app/services/jobs_service.py; tests/conftest.py; tests/test_api.py; tests/test_audit_jobs.py; tests/test_referrals.py
- **Test added:** tests/test_production_hardening.py::test_applying_requires_complete_onboarding
- **Notes:** Applying now requires every onboarding step to be complete and still valid; incomplete candidates receive 409 and no application row is created. Existing API tests complete onboarding first. The frontend already gated this path, so the change closes the backend bypass without a contract change.

- **Category:** Functional
- **Severity:** Medium
- **Location:** POST /api/jobs/{job_id}/apply; src/app/services/jobs_service.py:158-179.
- **What's wrong:** Observed: a newly registered candidate at 0% completion can apply without personal, professional, academic, or document data. The planned onboarding gate is absent at the authoritative backend boundary.
- **How to reproduce:** POST /api/auth/register with a unique valid identity, read /api/candidates/me to confirm completion=0, obtain an open job, then POST /api/jobs/<job>/apply. It returns 200 and creates an application visible to the job's agency.
- **Probable cause:** apply_to_job never loads or validates the candidate's onboarding state.
- **Suggested fix direction:** Enforce the agreed completion rule in the application service, with explicit tests for fresh and invalidated profiles.

### [BUG-010] Invalidated onboarding data still reports 100% complete

- **Status:** Fixed
- **What changed:** src/app/services/candidates_service.py
- **Test added:** tests/test_production_hardening.py::test_deleting_the_last_document_invalidates_onboarding
- **Notes:** Completing a step revalidates its saved data. Saving or deleting data that invalidates a completed step demotes that step to next and later steps to upcoming, so completion cannot report 100% while a required value is missing. Removing the last document invalidates the documents step.

- **Category:** Data integrity
- **Severity:** Medium
- **Location:** DELETE /api/candidates/me/documents/{id} and onboarding PUTs; src/app/services/candidates_service.py:113-117,238,252-334,384-390,463-472.
- **What's wrong:** Observed: after completing all steps, deleting the only document or clearing required profile/education/skills data leaves completion=100 and onboardingComplete=true.
- **How to reproduce:** Complete all four steps with valid data and one uploaded CV. Delete that CV: documents becomes empty but both completion indicators remain complete. PUT personal {} or academic {"education":[]} produces the same inconsistency.
- **Probable cause:** Completion derives solely from persisted step flags; saves/deletion do not invalidate them, and repeated completion returns before validation.
- **Suggested fix direction:** Revalidate affected steps and dependent transitions after edits/deletions; make the completion gate reflect current data.

### [BUG-011] Partial step saves erase omitted saved data

- **Status:** Fixed
- **What changed:** src/app/services/candidates_service.py; tests/test_audit_partial_save.py
- **Test added:** test_personal_partial_save_retains_saved_fields; test_professional_partial_save_retains_collections
- **Notes:** Both original partial-save scenarios failed before fix; 40 safe-suite tests passed after correction. Uses Pydantic field presence, including nested preferences and academic education; explicit empty values/arrays still clear. No request/response schema change.

- **Category:** Data integrity
- **Severity:** Medium
- **Location:** PUT /api/candidates/me/onboarding/{personal,professional,academic}; src/app/schemas/candidates_schema.py:91-97,135-140,172-173; src/app/services/candidates_service.py:252-334.
- **What's wrong:** Observed contract risk for resumable partial autosave: valid incomplete request bodies overwrite omitted fields with defaults. Previously saved experience/skills/education can disappear without an explicit deletion.
- **How to reproduce:** Save phone/location/headline; then PUT personal {"summary":"only this changed"}. The saved contact fields become empty. After saving professional data, PUT {"experienceLevel":"Mid","preferences":{"workType":"Remote"}} clears currentTitle, skills, experiences, and preference strings; PUT academic {} deletes all education.
- **Probable cause:** Optional schema defaults are applied as a full replacement, including clearing child collections. HTTP PUT replacement semantics may be intentional, but the accepted partial body and partial-save feature contract are not reconciled.
- **Suggested fix direction:** Make replacement requirements explicit, or implement field-preserving partial saves and explicit collection deletion semantics.

### [BUG-012] Agency supervisors can change authority in other agencies

- **Status:** Fixed
- **What changed:** src/app/services/staff_service.py
- **Test added:** tests/test_production_hardening.py::test_multi_agency_role_change_requires_platform_administration
- **Notes:** A supervisor can no longer change the global role of a member who also holds an active membership in another agency; that authority is reserved for platform administration. Team and active-flag changes remain available, and same-agency role changes still work.

- **Category:** Architecture
- **Severity:** Medium
- **Location:** PATCH /api/staff/members/{member_id}; src/app/services/staff_service.py:355-369; src/app/models/users_model.py:34.
- **What's wrong:** Observed design risk: a supervisor operating in one agency changes a global User.role, immediately affecting the target's authority in every other agency. The execution contract deliberately uses global roles; this is a consequence to review, not a claim that per-agency roles were promised.
- **How to reproduce:** Noor belongs to Northstar and Harbor. Create a second Northstar supervisor, sign Noor into Harbor in another client, and have the Northstar supervisor PATCH Noor with {"role":"employee"}. Harbor's session now reports employee, and Harbor job creation returns 403.
- **Probable cause:** Tenant-scoped team management writes a cross-tenant identity attribute.
- **Suggested fix direction:** Decide who may make global role changes; restrict that authority or define agency-scoped capabilities without silently broadening the approved architecture.

### [BUG-013] Deactivation counts the membership before its pending change is flushed

- **Status:** Fixed
- **What changed:** src/app/services/staff_service.py; tests/test_audit_fixes.py
- **Test added:** test_last_membership_deactivation_disables_identity
- **Notes:** Reproduced stale active identity before fix. Flush precedes remaining-membership count; replay verifies persisted inactive identity. Candidate targeting is separately denied by BUG-001.

- **Category:** Security
- **Severity:** Medium
- **Location:** PATCH /api/staff/members/{member_id}; src/app/database.py:44; src/app/services/staff_service.py:372-393; src/app/services/auth_service.py:150-154.
- **What's wrong:** Observed: deactivating a sole membership can leave User.is_active=true. For candidate targets accepted by BUG-001's endpoint, the next login succeeds as an independent candidate and expands job visibility across agencies.
- **How to reproduce:** Register a Northstar-referred candidate, then as Noor PATCH its user ID at /api/staff/members/<id> with {"active":false}. Read the test DB: membership is inactive but user remains active. Login again: 200, agency:null, and jobs from Northstar and Harbor.
- **Probable cause:** SessionLocal disables autoflush. The remaining-membership COUNT runs before the pending active=false is flushed and counts that membership as still active.
- **Suggested fix direction:** Make the count observe the new state and explicitly define candidate identity behavior after agency-access revocation. Existing staff sessions in the removed agency were correctly revoked.

### [BUG-014] The last supervisor can demote themselves and strand agency administration

- **Status:** Fixed
- **What changed:** src/app/services/staff_service.py
- **Test added:** tests/test_production_hardening.py::test_last_supervisor_cannot_demote_themselves
- **Notes:** Demoting or deactivating the last active supervisor of an agency returns 409. Deactivation already disabled the identity; the guard now prevents an agency from being left without administration.

- **Category:** Functional
- **Severity:** Medium
- **Location:** PATCH /api/staff/members/{member_id}; src/app/services/staff_service.py:364-369.
- **What's wrong:** Observed: self-deactivation is blocked, but self-demotion is allowed even when no other supervisor remains. The provided platform API has no agency-member recovery operation.
- **How to reproduce:** With the fresh seed, Northstar's only supervisor is Noor. PATCH /api/staff/members/<Noor user ID> with {"role":"employee"}. It returns 200; subsequent POST /api/jobs returns 403, as do supervisor-only team-management operations.
- **Probable cause:** There is no last-supervisor invariant or recovery/handover check on role changes.
- **Suggested fix direction:** Require an active successor or an explicitly authorized administrative recovery path before removing the final supervisor.

### [BUG-015] Referral signup assigns candidates to inactive referrers

- **Status:** Fixed
- **What changed:** src/app/services/referrals_service.py
- **Test added:** tests/test_production_hardening.py::test_deactivated_referrer_link_is_rejected
- **Notes:** A link resolves as inactive and registration returns 409 when its creator is inactive, lost the agency membership, or is no longer staff. Resolution and consumption share the same eligibility check.

- **Category:** Data integrity
- **Severity:** Medium
- **Location:** POST /api/auth/register using referralToken; src/app/services/referrals_service.py:60-105; src/app/services/auth_service.py:205-217.
- **What's wrong:** Observed: links remain usable after their creating employee is deactivated, and new candidates are automatically assigned to that inactive employee.
- **How to reproduce:** Sam creates a referral; Noor deactivates Sam in Northstar. Resolve the link and register with it. Registration returns 200 and the staff directory shows assignedTo=Sam's user ID while Sam is inactive.
- **Probable cause:** Consumption validates token status and agency status, but not the creator's current active staff membership.
- **Suggested fix direction:** Revoke/revalidate outstanding links on staff removal, or explicitly reroute their assignments to an active authorized agent.

### [BUG-016] Suspended-agency referral links resolve as valid

- **Status:** Fixed
- **What changed:** src/app/services/referrals_service.py; src/app/schemas/referrals_schema.py
- **Test added:** tests/test_production_hardening.py::test_referral_resolution_reports_suspended_agency
- **Notes:** A suspended agency makes the link resolve with status inactive and valid false, and consumption returns 409. The resolve status contract gains inactive; existing statuses are unchanged.

- **Category:** Functional
- **Severity:** Medium
- **Location:** GET /api/referrals/{token}; src/app/services/referrals_service.py:20-27,60-77; src/app/services/auth_service.py:207-209.
- **What's wrong:** Observed: resolve returns valid:true/status:active for an unexpired link whose agency is suspended, but registration rejects it. The public pre-signup answer is misleading.
- **How to reproduce:** Create a referral, suspend its agency as the platform admin, and GET /api/referrals/<token>: valid:true. POST /api/auth/register with it: 409, “That agency is not currently accepting referrals.” The failed signup correctly rolls back the new identity.
- **Probable cause:** resolve only examines expiry/use/revocation; the agency-status check exists later in registration.
- **Suggested fix direction:** Make resolution reflect current signup eligibility and return a clear inactive-agency reason.

### [BUG-017] Login to a suspended agency succeeds with an unusable session

- **Status:** Fixed
- **What changed:** src/app/services/auth_service.py
- **Test added:** tests/test_production_hardening.py::test_suspended_agency_login_is_rejected
- **Notes:** Login rejects accounts whose memberships are all in suspended agencies with 403 and no session cookie, and an explicitly requested suspended agency is also rejected. Platform administrators still require no agency. Password verification happens first, so suspended-agency attempts do not leak account state differently.

- **Category:** Functional
- **Severity:** Medium
- **Location:** POST /api/auth/login and /demo-login; src/app/services/auth_service.py:145-177,242-251 versus 90-117.
- **What's wrong:** Observed: login issues cookies and returns 200 for an active membership in a suspended agency, but the next request treats that session as invalid. A multi-agency user can also default to an unavailable first agency.
- **How to reproduce:** Suspend Northstar as Jules, then login as sam@demo.example.com. Login returns 200 with Northstar context; GET /api/auth/session returns null and GET /api/staff/workspace returns 401.
- **Probable cause:** _resolve_login_agency checks membership.active but not agency.status; resolve_session checks both.
- **Suggested fix direction:** Apply the same agency eligibility rules during login, with an explicit alternate-context flow where applicable.

### [BUG-018] Concurrent duplicate registration and application return unhandled 500s

- **Status:** Fixed
- **What changed:** src/app/main.py
- **Test added:** tests/test_api.py::test_register_login_and_duplicate_email; tests/test_production_hardening.py::test_unexpected_integrity_error_returns_conflict
- **Notes:** Explicit duplicate checks remain the normal 409 path. A global IntegrityError handler now maps a losing concurrent insert to 409 instead of an unhandled 500. The handler is covered directly; the concurrency race itself was not load-tested.

- **Category:** Data integrity
- **Severity:** Medium
- **Location:** POST /api/auth/register and /api/jobs/{job_id}/apply; src/app/services/auth_service.py:187-202; src/app/services/jobs_service.py:164-189; src/app/main.py:121-123.
- **What's wrong:** Observed: unique constraints preserve one record, but competing requests race past preflight checks and the loser returns plain 500 instead of a controlled conflict.
- **How to reproduce:** With two local clients, submit the same previously unused email concurrently; separately submit the same candidate/job application concurrently. To reproduce deterministically, attach a SQLAlchemy after_cursor_execute listener that waits on threading.Barrier(2) after each matching existence SELECT, then release both requests together. Registration produced [200,500]; applications produced [200,500], with exactly one application stored.
- **Probable cause:** Check-then-insert logic does not translate database uniqueness errors. By contrast, concurrent single-use referral signup produced [200,409] and one winner.
- **Suggested fix direction:** Keep constraints authoritative and map known conflicts after rollback; test actual competing transactions on PostgreSQL too.

### [BUG-019] Document filesystem and database writes can diverge on failure

- **Status:** Fixed
- **What changed:** src/app/services/candidates_service.py
- **Test added:** tests/test_production_hardening.py::test_upload_removes_the_file_when_the_database_write_fails
- **Notes:** Upload writes the file, commits metadata, and unlinks the file if the write fails. Delete renames the file to a hidden tombstone, deletes metadata, and restores the file if the database step fails. A leftover tombstone is logged and is never downloadable.

- **Category:** Data integrity
- **Severity:** Medium
- **Location:** POST/DELETE /api/candidates/me/documents; src/app/services/candidates_service.py:433-450,463-471.
- **What's wrong:** Injected failures: upload writes a file before database commit, leaving an orphan if the commit fails. Delete commits removal of metadata before unlinking; a locked file then yields 500 while retaining bytes with no accessible document record.
- **How to reproduce:** Attach a temporary SQLAlchemy Session.before_flush listener that raises when a new Document is present, then upload a PDF: 500 and one extra file, no committed row. Separately upload a document and patch Path.unlink to raise PermissionError during DELETE: 500, metadata absent, file still present.
- **Probable cause:** Filesystem effects have no compensation/reconciliation around the database transaction.
- **Suggested fix direction:** Stage uploads and compensate failed commits; make deletions retryable/reconcilable while preserving enough metadata to clean retained bytes.

### [BUG-020] Four signature bytes are enough to pass document validation

- **Status:** Fixed
- **What changed:** src/app/services/candidates_service.py
- **Test added:** tests/test_document_limits.py::test_document_structure_must_match_its_type; ::test_storage_extension_comes_from_type
- **Notes:** Validation now requires a complete PDF trailer, a DOCX zip containing [Content_Types].xml and word/document.xml, or the OLE header for DOC. Stored extensions come from the validated MIME type, not the submitted filename. This is structural validation, not malware scanning.

- **Category:** Functional
- **Severity:** Medium
- **Location:** POST /api/candidates/me/documents; src/app/services/candidates_service.py:410-430.
- **What's wrong:** Observed: malformed non-documents are accepted as CVs and can satisfy the documents requirement. A DOCX only has to look like the beginning of any ZIP file.
- **How to reproduce:** Upload invalid.pdf with bytes b"%PDF" and MIME application/pdf: 200. Upload not-word.docx with bytes b"PK\x03\x04garbage" and the DOCX MIME: 200, although it contains no valid ZIP/Word structure.
- **Probable cause:** _matches_signature only checks a four-byte prefix and never parses a minimal valid document structure.
- **Suggested fix direction:** Validate format structure within strict resource bounds, and define any malware/macro policy separately. No uploaded-file execution or downstream parser exploitation was established.

### [BUG-021] Unbounded upload filenames can produce filesystem errors

- **Status:** Fixed
- **What changed:** src/app/services/candidates_service.py
- **Test added:** tests/test_document_limits.py::test_long_filename_returns_validation_error
- **Notes:** Filenames are reduced to a basename, length-bounded, and rejected when empty, dot-only, or containing control characters. Stored names are generated IDs; the original name is metadata only.

- **Category:** Functional
- **Severity:** Medium
- **Location:** POST /api/candidates/me/documents; src/app/services/candidates_service.py:435-444; src/app/models/candidates_model.py:163.
- **What's wrong:** Observed on Windows: a long filename suffix is copied into the physical UUID filename and raises an unhandled filesystem error. Filename length is also unbounded relative to the 255-character database column.
- **How to reproduce:** Upload a small valid-prefix PDF with filename "cv." + "a" * 300 and MIME application/pdf. The endpoint returns plain 500 instead of a validation error.
- **Probable cause:** The service trusts Path(filename).suffix for the disk name and has no filename/extension bound or storage-error mapping.
- **Suggested fix direction:** Derive a short allowlisted extension from validated format, bound display names, and map storage failures predictably.

### [BUG-022] Whitespace and empty strings bypass required-field validation

- **Status:** Fixed
- **What changed:** src/app/schemas/auth_schema.py; src/app/schemas/jobs_schema.py; src/app/schemas/candidates_schema.py; src/app/schemas/staff_schema.py
- **Test added:** tests/test_production_hardening.py::test_blank_and_oversized_inputs_are_rejected
- **Notes:** Required free-text fields are trimmed and rejected when blank; optional text is trimmed; whitespace-only passwords are rejected while password bytes are preserved. Validation runs at the schema boundary for registration, jobs, onboarding, and team members.

- **Category:** Functional
- **Severity:** Medium
- **Location:** Registration, job create/patch, academic save/complete; src/app/schemas/auth_schema.py:31-34; src/app/schemas/jobs_schema.py:46-64; src/app/schemas/candidates_schema.py:156-169; src/app/services/candidates_service.py:378-379.
- **What's wrong:** Observed: required fields can become empty after trimming, and job PATCH permits empty required strings. Academic completion accepts education entries with blank institution/degree.
- **How to reproduce:** Register {"name":"   ","email":"blank@example.com","password":"        "}: 200 with empty user.name. PATCH a job with {"title":""}: 200 with empty title. At academic, save {"education":[{"institution":" ","degree":" ","startYear":2020}]} and complete it: 200, blank institution/degree persisted, completion advances to 75%.
- **Probable cause:** min_length is evaluated before service trimming; patch fields omit minimums; academic completion checks only collection presence.
- **Suggested fix direction:** Normalize before validation, enforce nonblank required values consistently on create/update/completion, and explicitly define password whitespace policy.

### [BUG-023] Valid inputs generate activity text too long for PostgreSQL columns

- **Status:** Not reproducible
- **What changed:** No implementation change for this finding.
- **Test added:** None; not closed.
- **Notes:** Verification blocked, not a false-positive determination. PostgreSQL VARCHAR enforcement cannot be reproduced locally. Recommend bounded derived activity messages versus a reviewed column-widening migration. Never apply an unverified data-altering migration.

- **Category:** Functional
- **Severity:** Medium
- **Location:** POST /api/jobs/{job_id}/apply; src/app/services/jobs_service.py:181-189; src/app/models/staff_model.py:44; related derived log text in jobs/staff services.
- **What's wrong:** Observed length mismatch, PostgreSQL failure unverified: allowed candidate and job names produce an Activity.title exceeding VARCHAR(200). SQLite accepts it, while PostgreSQL is expected to reject the activity insert and roll back the application.
- **How to reproduce:** Register a name of 120 N characters; create a job title of 160 T characters; apply to it. SQLite returns 200 and stores a **292-character** activity title in a column declared length 200. Repeat on a disposable PostgreSQL database to confirm its rejection.
- **Probable cause:** Derived descriptions concatenate independently valid inputs without checking the destination column bound.
- **Suggested fix direction:** Choose adequate log storage or bound composed text intentionally; test maximum valid combinations on the canonical database.

### [BUG-024] Job tag strings have no size bound

- **Status:** Fixed
- **What changed:** src/app/schemas/jobs_schema.py
- **Test added:** tests/test_production_hardening.py::test_blank_and_oversized_inputs_are_rejected
- **Notes:** Each tag is trimmed and capped at 40 characters, and the existing 12-tag limit is unchanged. Oversized tags now return 422 instead of a database error.

- **Category:** Performance
- **Severity:** Medium
- **Location:** POST /api/jobs and PATCH /api/jobs/{id}; src/app/schemas/jobs_schema.py:52,62; src/app/services/jobs_service.py:123,148-149.
- **What's wrong:** Observed: tag count is limited to 12, but each tag can be arbitrarily large. A single large tag is stored and repeated in every workspace response containing that job.
- **How to reproduce:** As a supervisor, create a valid job with tags=["x" * 1048576]. It returns 200. In the enlarged test dataset, the mutation response grew to **3,304,261 bytes**, about 1 MB above the already oversized workspace.
- **Probable cause:** list[str] constrains only the number of tags, with no per-string or aggregate payload bound.
- **Suggested fix direction:** Limit individual tags and aggregate request size; return bounded result data after mutations.

### [BUG-025] Document storage has no per-user count or aggregate quota

- **Status:** Fixed
- **What changed:** src/app/config.py; src/app/services/candidates_service.py
- **Test added:** tests/test_document_limits.py::test_document_count_quota; ::test_document_aggregate_quota
- **Notes:** Per-candidate limits of MAX_DOCUMENTS_PER_CANDIDATE (default 10) and MAX_CANDIDATE_DOCUMENT_BYTES (default 50 MB) are enforced while holding a per-candidate lock, before the file is written. The lock is in-process on SQLite and a row lock on PostgreSQL.

- **Category:** Performance
- **Severity:** Medium
- **Location:** POST /api/candidates/me/documents and GET /api/candidates/me; src/app/services/candidates_service.py:418-451,182-236.
- **What's wrong:** Observed/source-reviewed: any candidate can accumulate unlimited accepted files, each up to 10 MB, with all metadata loaded into the workspace. Registration is public and has no abuse cap.
- **How to reproduce:** Upload 24 small valid-prefix PDFs as one candidate; all 24 return 200 and all 24 are listed. No count/aggregate check appears in add_document. The test used tiny files and did not fill the disk.
- **Probable cause:** Only individual content length is checked; there is no user/storage quota or document-count rule.
- **Suggested fix direction:** Define a justified count/aggregate quota and enforce it atomically, with bounded metadata retrieval.

### [BUG-026] Workspaces and referral lists grow without pagination

- **Status:** Mitigated
- **What changed:** src/app/config.py; src/app/services/jobs_service.py; src/app/services/staff_service.py; src/app/services/candidates_service.py
- **Test added:** No dedicated test; existing workspace suites exercise the capped queries.
- **Notes:** Every workspace list query now has a deterministic order and a hard row cap (MAX_WORKSPACE_ITEMS, default 500), bounding response work. This is not real pagination: clients cannot page past the cap and no cursor or limit contract exists. Pagination remains backlog work.

- **Category:** Performance
- **Severity:** Medium
- **Location:** GET /api/jobs/workspace, /staff/workspace, /platform/workspace, /referrals and their mutation responses; src/app/services/jobs_service.py:60-92; staff_service.py:103-172; platform_service.py:16-75; referrals_service.py:142-148.
- **What's wrong:** Observed: jobs/applications/candidates/team members/agencies/integrations/referral links are loaded without a page/limit/filter contract. Most writes rerender the entire workspace. Only activity/audit subsections have caps.
- **How to reproduce:** Insert 1,000 synthetic open jobs with 2,000-character descriptions into the test DB, then GET /api/jobs/workspace. It returns all jobs in **2,254,565 bytes**. Eight-worker/16-request load gives median 551.29 ms, p95 710.40 ms, versus median 137.10 ms/p95 172.43 ms on the seeded workload. Requests with unimplemented pagination parameters do not bound the queries.
- **Probable cause:** Workspace aggregation is the only read contract; services materialize complete collections and full job descriptions.
- **Suggested fix direction:** Add bounded resource reads and narrower mutation responses, preserving the current frontend contract through an explicit integration plan. No compression middleware or response cache is configured in this API.

### [BUG-027] Staff and platform workspaces execute N+1 queries

- **Status:** Fixed
- **What changed:** src/app/services/staff_service.py; src/app/services/platform_service.py; tests/test_audit_queries.py
- **Test added:** test_workspace_counts_do_not_grow_per_record (both roles)
- **Notes:** Before fix +10 staff/agencies caused +10 queries. Original replay now bounded; 37 safe-suite tests passed. Staff derives workloads from already loaded assignments; platform counts memberships once grouped by agency.

- **Category:** Performance
- **Severity:** Medium
- **Location:** GET /api/staff/workspace and /api/platform/workspace; src/app/services/staff_service.py:93-100,149-159; src/app/services/platform_service.py:21-27.
- **What's wrong:** Observed with SQLAlchemy statement instrumentation: staff runs a separate workload COUNT per member; platform runs a separate membership COUNT per agency.
- **How to reproduce:** Baseline request counts were staff=21 and platform=11 SQL statements. Add 100 synthetic staff memberships and 100 agencies, then repeat: staff=121, platform=111. Single-request elapsed times grew from 26.61→77.21 ms and 14.17→69.02 ms respectively on this local SQLite run.
- **Probable cause:** Aggregate counts are queried inside serialization loops rather than grouped once.
- **Suggested fix direction:** Retrieve grouped counts in bounded queries. Existing selectinload use in other relationship paths should be retained.

### [BUG-028] Tenant filters and session revocation lack supporting indexes

- **Status:** Fixed
- **What changed:** alembic/versions/a7d2e5c91f04_workspace_indexes.py; tests/test_migrations.py
- **Test added:** tests/test_migrations.py::test_migrations_create_and_drop_schema
- **Notes:** Additive migration a7d2e5c91f04 adds tenant and session indexes for jobs, applications, activities, auth_sessions, memberships, candidate_assignments, and referral_links. Upgrade and downgrade pass on a disposable SQLite database; PostgreSQL execution is a deployment prerequisite.

- **Category:** Performance
- **Severity:** Medium
- **Location:** Workspace, activity, password/deactivation queries; src/app/models/jobs_model.py:15,38-40; staff_model.py:40,47; users_model.py:67-75; initial migration index definitions.
- **What's wrong:** Observed planner evidence: tenant/time queries scan jobs, applications, and activities, while session revocation scans auth_sessions by user. Existing unique indexes do not cover all leading filter columns.
- **How to reproduce:** On the enlarged test DB, EXPLAIN QUERY PLAN SELECT * FROM jobs WHERE agency_id=:id ORDER BY created_at DESC reports SCAN jobs plus a temporary sort. Candidate application history similarly reports SCAN applications; recent activity reports SCAN activities plus sort; auth_sessions WHERE user_id=:id AND revoked_at IS NULL reports SCAN auth_sessions.
- **Probable cause:** Indexes mostly cover primary keys/uniques and new normalized tables; frequently used agency/user/time predicates were not indexed.
- **Suggested fix direction:** Add query-driven composite indexes via migrations after checking PostgreSQL plans and representative cardinalities.

### [BUG-029] Private responses lack explicit cache protection

- **Status:** Fixed
- **What changed:** src/app/main.py; tests/test_audit_headers.py
- **Test added:** test_private_responses_are_not_cacheable
- **Notes:** Original missing-header repro failed; safe suite passed 33 tests after adding no-store to normal responses. Browser cache/proxy behavior remains deployment verification. Adds nosniff/frame/referrer protection; docs CSP remains BUG-036.

- **Category:** Security
- **Severity:** Medium
- **Location:** GET /api/auth/session, private workspaces and document downloads; src/app/main.py:101-123; src/app/controllers/auth_controller.py:27-31; candidates_controller.py:81-91.
- **What's wrong:** Observed headers, deployment risk: sensitive GET responses contain neither Cache-Control: no-store nor an explicit private policy; they also do not vary by Cookie. Shared-cookie HTTP responses need a deliberate cache policy. An actual proxy/cache data leak was not demonstrated.
- **How to reproduce:** Login and inspect headers on /api/auth/session, /api/candidates/me, and an authorized document download. The session response contained content-length, content-type, and Vary: Origin, without Cache-Control. Document responses additionally provide validators such as ETag/Last-Modified.
- **Probable cause:** No private-response cache policy exists in middleware/controllers.
- **Suggested fix direction:** Explicitly prevent credential/session/private-document caching and define any permitted workspace caching at the deployment boundary.

### [BUG-030] Async upload handler runs blocking filesystem and database work

- **Status:** Fixed
- **What changed:** src/app/controllers/candidates_controller.py; tests/test_audit_upload_thread.py
- **Test added:** test_upload_service_does_not_block_event_loop
- **Notes:** Original thread-identity repro failed: upload read and blocking service shared loop thread. Replay verifies separate worker thread; 41 safe-suite tests passed. Starlette's existing run_in_threadpool used, no dependency or wire contract change.

- **Category:** Performance
- **Severity:** Medium
- **Location:** POST /api/candidates/me/documents; src/app/controllers/candidates_controller.py:66-78; src/app/services/candidates_service.py:433-451.
- **What's wrong:** Observed under injected latency: the async endpoint calls synchronous SQLAlchemy, directory creation, file writing, commit, and workspace loading directly on the event loop. Slow storage/database work stalls other coroutine processing in that worker.
- **How to reproduce:** Use a single httpx.ASGITransport/asyncio event loop with a 5 ms ticker alongside upload. Temporarily wrap candidates_service.add_document with a 250 ms synchronous sleep before invoking the original. Upload succeeds, but the largest ticker gap was **333.82 ms**.
- **Probable cause:** File.read is awaited, then the controller calls a blocking service without thread offloading.
- **Suggested fix direction:** Run the synchronous service in the appropriate worker thread, or use a consistently asynchronous I/O design. The delay was simulated; 333.82 ms is not a measured normal storage latency.

### [BUG-031] Expired and revoked session rows have no cleanup policy

- **Status:** Fixed
- **What changed:** src/app/config.py; src/app/services/auth_service.py; src/app/main.py
- **Test added:** tests/test_production_hardening.py::test_expired_sessions_are_purged
- **Notes:** Startup deletes expired or revoked session rows older than SESSION_RETENTION_DAYS (default 7). Runtime validation already rejected expired and revoked sessions; this bounds table growth. A failed purge is logged and does not block startup.

- **Category:** Architecture
- **Severity:** Medium
- **Location:** Authentication lifecycle; src/app/services/auth_service.py:62-77,90-95,254-256,277-290; src/app/models/users_model.py:63-75.
- **What's wrong:** Observed/source-reviewed: every login appends a session; logout/password changes only mark rows revoked; expiry only rejects them. There is no cleanup operation, retention limit, or indexed expiration strategy in the repository.
- **How to reproduce:** Count auth_sessions, perform five logout/login cycles for one test account, then count again: 8→13 in the isolated run. Expire/revoke a row and read the session; it is rejected but retained.
- **Probable cause:** The lifecycle implements validity/revocation without bounded retention.
- **Suggested fix direction:** Define session retention and a bounded cleanup mechanism; distinguish needed audit records from disposable session credentials. Multiple valid device sessions alone are not reported as a bug.

### [BUG-032] Repeated onboarding saves replace record IDs despite supplied IDs

- **Status:** Fixed
- **What changed:** src/app/services/candidates_service.py
- **Test added:** tests/test_production_hardening.py::test_onboarding_child_ids_are_stable
- **Notes:** Experience and education saves reuse the row with the supplied id and only create rows without one, so autosave no longer churns identifiers. Lookups are scoped to the loaded candidate profile, so a foreign id cannot address another candidate's row.

- **Category:** Data integrity
- **Severity:** Medium
- **Location:** PUT professional/academic onboarding; src/app/schemas/candidates_schema.py:109,157; src/app/services/candidates_service.py:266-280,319-330.
- **What's wrong:** Observed for experience, same code pattern for education: input accepts an id, but the service discards it and recreates all records. An unchanged PUT is not stable with respect to publicly returned IDs.
- **How to reproduce:** Save one experience and capture experiences[0].id. Repeat the same professional payload, including that ID. The returned ID changes; the old record has been removed.
- **Probable cause:** Clear-and-append replacement ignores supplied IDs and always invokes new UUID defaults.
- **Suggested fix direction:** Preserve authorized existing child identities or remove identity-bearing inputs and clearly specify replace-all semantics. Test client reconciliation and autosave retries.

### [BUG-033] Non-ASCII CSRF headers raise an unhandled exception

- **Status:** Fixed
- **What changed:** src/app/security.py; tests/test_audit_csrf.py
- **Test added:** test_non_ascii_csrf_is_denied
- **Notes:** Reproduced plain 500 before fix; replay now returns existing 403 CSRF rejection. Safe suite 34 passed; both header and cookie checked for ASCII. Client-visible malformed-input correction flagged below.

- **Category:** Functional
- **Severity:** Low
- **Location:** Authenticated mutation routes; src/app/security.py:24-29.
- **What's wrong:** Observed: a non-ASCII header reaches secrets.compare_digest with a str input that it cannot compare, returning 500 rather than the normal CSRF denial.
- **How to reproduce:** Login as a candidate; with TestClient send POST /api/candidates/me/onboarding/missing/complete using headers=[(b"X-CSRF-Token", b"\xff")]. It returns plain 500. An ordinary wrong ASCII token returns 403.
- **Probable cause:** The helper assumes ASCII before calling compare_digest; tokens are not validated/decoded into an accepted representation first.
- **Suggested fix direction:** Validate token encoding/shape and return the standard 403 for malformed values.

### [BUG-034] Failed-login timing reveals whether an email exists

- **Status:** Fixed
- **What changed:** src/app/services/auth_service.py; tests/test_audit_timing.py
- **Test added:** test_unknown_login_still_verifies_password
- **Notes:** Before fix absent account skipped hashing; replay calls password verifier once. Safe suite 35 passed. Random dummy password hash generated at process start; no new secret/env or dependency. Exact network timing cannot be equalized. Unknown-user requests now incur Argon2 cost; BUG-006 rate limits remain important.

- **Category:** Security
- **Severity:** Low
- **Location:** POST /api/auth/login; src/app/services/auth_service.py:168-170.
- **What's wrong:** Observed: identical incorrect-password responses take substantially different paths for unknown versus known emails.
- **How to reproduce:** Make ten local wrong-password requests for missing@example.com and ten for seeded sam@demo.example.com. Both return the same 401 text; medians were **8.44 ms** and **86.80 ms**, respectively.
- **Probable cause:** Unknown users short-circuit before the password hash verification.
- **Suggested fix direction:** Use equivalent dummy verification for absent accounts and apply abuse controls. Network conditions can blur the signal; no real-user enumeration was attempted.

### [BUG-035] Health endpoint provides no database readiness signal

- **Status:** Fixed
- **What changed:** src/app/main.py
- **Test added:** tests/test_production_hardening.py::test_readiness_endpoint_reports_database
- **Notes:** GET /api/ready runs SELECT 1 and returns 200 ok or 503 unavailable; GET /api/health stays a liveness check. The container healthcheck calls /api/ready.

- **Category:** Architecture
- **Severity:** Low
- **Location:** GET /api/health; src/app/main.py:125-127; compose.yaml.
- **What's wrong:** Observed/design gap: health always returns status:ok without consulting the database/schema. This is valid as liveness, but there is no separate API readiness endpoint or API-service healthcheck to detect an unusable database.
- **How to reproduce:** Temporarily make engine.connect raise in the isolated process, then GET /api/health: 200 {"status":"ok"}. The endpoint never calls the database.
- **Probable cause:** Health is implemented as a constant response; Compose only healthchecks PostgreSQL itself.
- **Suggested fix direction:** Keep liveness simple and add an explicitly named bounded readiness check for required dependencies/schema.

### [BUG-036] Direct API and docs responses omit browser hardening headers

- **Status:** Fixed
- **What changed:** src/app/main.py; src/app/config.py; Dockerfile; compose.yaml; compose.production.yaml
- **Test added:** tests/test_audit_headers.py; tests/test_production_security.py
- **Notes:** Adds Permissions-Policy, Cross-Origin-Resource-Policy, and a restrictive CSP to every response (with a Swagger-only HTML policy), optional HSTS via HSTS_SECONDS, TrustedHostMiddleware when TRUSTED_HOSTS is set, and forwarded-header trust only for FORWARDED_ALLOW_IPS. The documented topology is edge or CDN to the Next.js rewrite to FastAPI on loopback. No proxy is deployed or tested here, so TLS, WAF, and edge per-IP limits remain a hosting decision.

- **Category:** Security
- **Severity:** Low
- **Location:** GET /docs and API responses; src/app/main.py:94-123.
- **What's wrong:** Observed on direct responses: no X-Content-Type-Options, frame protection, or explicit Referrer-Policy is configured; docs also have no CSP. TLS/HSTS or header protection supplied by an external proxy could mitigate this, but no deployed proxy was tested.
- **How to reproduce:** Inspect headers on GET /docs, /api/auth/session, and a file download in TestClient. No middleware adds the above protections.
- **Probable cause:** Application middleware covers CORS/origin checks only.
- **Suggested fix direction:** Define the application's versus proxy's header responsibilities, including a docs-compatible CSP and transport policy where HTTPS terminates. This finding does not establish an XSS exploit.

### [BUG-037] OpenAPI describes document downloads as JSON

- **Status:** Fixed
- **What changed:** src/app/controllers/candidates_controller.py; tests/test_audit_download_contract.py
- **Test added:** test_document_download_documents_binary_content
- **Notes:** Original OpenAPI repro failed before fix; binary media schemas now declared. Actual bytes/routes/status unchanged. 38 safe-suite tests passed. Regenerate clients only after reviewing corrected download metadata.

- **Category:** Architecture
- **Severity:** Low
- **Location:** GET /api/candidates/me/documents/{document_id}; src/app/controllers/candidates_controller.py:81-91.
- **What's wrong:** Observed: OpenAPI advertises application/json with an empty schema for 200, while the route returns binary PDF/Word bytes and supports range responses.
- **How to reproduce:** GET /openapi.json and inspect that operation's responses.200.content: application/json. Download an uploaded PDF and compare its Content-Type and bytes; Range requests return 206/416.
- **Probable cause:** FileResponse is returned from the function but is not declared as the route's response contract.
- **Suggested fix direction:** Document actual binary media types and relevant response statuses so generated clients handle downloads correctly.

## Performance and stress evidence

Tests ran in-process against isolated local SQLite using the actual ASGI app. Concurrency included TestClient/thread scheduling overhead; timings are comparative workstation observations, not HTTP-network or PostgreSQL capacity measurements. P95 is the sorted sample's 95th-percentile observation.

| Scenario | Concurrency / requests | Statuses | Median ms | P95 ms | Largest response |
| --- | --- | --- | --- | --- | --- |
| Seed staff workspace | 8 workers / 48 | 48 × 200 | 220.71 | 292.34 | 2,954 bytes |
| Seed candidate jobs | 8 / 48 | 48 × 200 | 137.10 | 172.43 | 2,675 bytes |
| Seed platform workspace | 8 / 48 | 48 × 200 | 124.47 | 159.22 | 1,942 bytes |
| Seed session read | 8 / 48 | 48 × 200 | 75.12 | 108.04 | 194 bytes |
| Wrong password for existing account | 8 / 32 | 32 × 401; no 429 | 333.12 | 392.73 | 44 bytes |
| Jobs after adding 1,000 rows | 8 / 16 | 16 × 200 | 551.29 | 710.40 | 2,254,565 bytes |
| Forced duplicate application race | 2 / 2 | 200 + 500; one row stored | — | — | 3,303,457 bytes for success after large-tag fixture |
| Forced duplicate registration race | 2 / 2 | 200 + 500 | — | — | 186 bytes for success |
| Concurrent single-use referral registration | 2 / 2 | 200 + 409 | — | — | 341 bytes for success |

Separate single-request SQL counts: staff 21→121 with 100 added members; platform 11→111 with 100 added agencies. Jobs stayed at eight statements in the measured independent-candidate path, showing bounded relationship query count but unbounded rows/payload. This distinguishes N+1 from simple volume growth.

A bounded memory/connection smoke test warmed 40 session reads, then performed 200 further reads and garbage collection. Python traced live allocations grew 39,531→83,510 bytes (+43,979); peak traced allocations were 553,398 bytes. The engine ended with five pooled connections, zero overflow, and **zero checked-out connections**. This short run did not establish a memory leak; it also cannot rule out long-term RSS, driver, or deployment leaks. No crash occurred in the ordinary bounded bursts; deliberate race, malformed-header/filename, and failure-injection cases returned the reported 500s.

## Reproducing safely without touching the configured database

The HTTP steps above assume the following isolation setup, or an equivalent separately verified test database. Run from backend using its existing Python executable; place a chosen issue's HTTP calls at the marked point. All request IDs must come from this generated test dataset.

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
@'
import os, sys, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="jf-bugs-repro-") as directory:
    root = Path(directory)
    os.environ.update(
        DATABASE_URL="sqlite:///" + (root / "test.db").as_posix(),
        DOCUMENT_DIR=str(root / "documents"),
        SEED_ON_STARTUP="false",
        DEMO_LOGIN_ENABLED="true",
        DOCS_TESTING_ENABLED="false",
        COOKIE_SECURE="false",
        CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000",
        SESSION_DAYS="7",
        MAX_UPLOAD_BYTES=str(10 * 1024 * 1024),
    )
    sys.path.insert(0, str(Path("src").resolve()))
    from app.database import engine
    from app.main import app
    from app.seed import seed
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    assert engine.url.drivername == "sqlite"
    assert Path(engine.url.database).resolve().parent == root.resolve()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        seed()
        with TestClient(app, raise_server_exceptions=False) as client:
            login = client.post("/api/auth/login",
                json={"email":"noor@demo.example.com","password":"Demo1234!"},
                headers={"Origin":"http://localhost:3000"})
            assert login.status_code == 200, login.text
            headers = {"Origin":"http://localhost:3000",
                "X-CSRF-Token":client.cookies.get("jf_csrf")}
            # Perform one issue's requests here, using this client/test DB only.
    finally:
        engine.dispose()
'@ | .venv\Scripts\python.exe -B -
~~~

The audit suite itself was invoked through pytest.main with -q -p no:cacheprovider and an OS-temporary --basetemp, rather than allowing pytest to write a repository cache. tests/conftest.py creates its own isolated directory; the audit wrapper disposed its engine and removed that directory after the run. Ruff was run as .venv/Scripts/ruff.exe check . --no-cache. No package synchronization or lockfile regeneration was performed.

## Tested and clean, within the stated scope

- All **33 API operations** exercised, plus public docs/OpenAPI/OAuth redirect. All **115** anonymous/wrong-role checks behaved as expected for the tested generic routes. The candidate-target and application-scope exceptions are recorded separately above.
- Individual/referral registration creates the expected membership context and normalized workspace; successful referrals preserve assignment/context after login. Unknown, expired, revoked, and used links reject signup. Concurrent single-use consumption produced one winner and a controlled 409; rejected suspended-agency signup left no new user.
- Correct ordinary login/logout/password changes work. Password change and logout invalidate replayed session tokens; expired, forged opaque tokens and JWT-shaped values do not authenticate. The server stores hashed high-entropy tokens and Argon2 password hashes. Existing-session reuse across another login was observed but is consistent with multiple-device sessions and is not listed as a defect.
- Missing/wrong CSRF tokens and hostile origins are rejected; hostile-origin preflight returned 400 with no allow-origin header. Explicit COOKIE_SECURE=true produced Secure, HttpOnly, Path=/, SameSite=Lax session cookies; the CSRF cookie was deliberately readable and Secure.
- Own-candidate data and documents load correctly. Other candidates and staff cannot download a candidate's private document. Filename path components were stripped in the tested traversal-style upload; physical storage used server-generated UUID names. Missing rows/files returned controlled errors; valid/invalid file ranges returned 206/416.
- Ordered onboarding, required-personal checks, valid professional/academic data, and logout/login resumption work for newly created candidates. Invalid experience/education ordering is schema-validated. Exceptions for legacy migration, blank content, stale completion, and replacement are above.
- Staff assignment/unassignment, stage updates, team creation/update, ordinary staff deactivation/session revocation, job creation/close/reopen, application status propagation, agency switching, platform isolation, and agency suspend/reactivate/audit flows work on ordinary inputs. Cross-agency assignment/member/job/application mutations were denied in the tested cases.
- The **332-request field/body probe** produced 304 × 422, 19 × 404, 4 × 409, 4 × 200, and 1 × 403, with no 500s in that generic set. Additional Unicode-token and long-filename probes exposed the separately logged 500s. Ordinary invalid fields, missing bodies, wrong enums/types, nulls, large bounded strings, missing IDs, and unsupported methods were exercised. Permissive Pydantic coercions and ignored unknown fields were observed; no role/agency mass assignment via registration was established.
- SQL-like ID strings returned 404; reviewed application queries use SQLAlchemy binding, and migration raw SQL uses fixed text/bind parameters. No request-driven eval, shell commands, unsafe deserialization, or outbound fetch implementation was found. javascript:/file: portfolio links were rejected; an HTTP loopback URL was stored without fetching it. XSS-style text was returned as JSON data, not executed HTML; this does not verify downstream browser sinks.
- Empty SQLite upgrade/downgrade passed in the suite. A populated legacy upgrade preserved tested skills, preferences, and document metadata, with PRAGMA foreign_key_check returning no violations; the onboarding-state defect is above. Re-seeding a populated head database returned false and preserved checked row counts.
- OSV's [version-specific batch API](https://google.github.io/osv.dev/post-v1-querybatch/) returned **no advisory matches for 75 installed third-party distributions and all 77 locked registry packages**. Only public package names/versions were transmitted; no code, environment contents, credentials, or user data were sent. This is a point-in-time advisory lookup, not proof that dependencies are vulnerability-free.
- No checked-out connection leak or crash was observed in the bounded normal-load smoke tests.

## Not tested or not established

- **PostgreSQL and Docker:** neither toolchain/server was available locally; no PostgreSQL listener was found. No existing external database was contacted. PostgreSQL migrations, integer/boolean handling, VARCHAR enforcement, production query plans, locking/isolation differences, Compose startup, restart persistence, and container health remain unexecuted. BUG-003 and the PostgreSQL failure consequence of BUG-023 are explicitly static findings.
- **Real browser and deployment boundary:** no frontend end-to-end/browser XSS, browser-cache, CSRF navigation exploit, TLS/proxy/header policy, public network exposure, or production-cookie configuration was tested. The backend's direct behavior and configured template were audited; deployment risks are conditional.
- **Long-duration or destructive load:** no soak test, disk/memory exhaustion, password cracking, multi-GB body, distributed attack, real malware execution, or production traffic replay. Bounds were eight ordinary load workers, two competing writers, 1,000 added jobs, 100 members/agencies, a 1 MB tag, 24 tiny document uploads, and an 11 MB oversized unauthenticated file.
- **External integrations/workers:** integrations are simulated records; there is no Celery/Redis implementation or real third-party worker to exercise. Email verification/delivery, OAuth, payments, chat/F02, and unavailable endpoints were not treated as implemented features.
- **Filesystem/DB faults:** selected commit/unlink/latency paths were injected and reproduced; full disk, process termination at every write boundary, backups/restores, and every OS permission failure were not exhaustively simulated.
- **Secrets and alternative-model consultation:** real .env contents, production credentials, and real-user datasets were not inspected or sent anywhere. No DeepSeek/opencode consultation was needed; approved contracts and current source were sufficient. Source code was not changed.



## Audit fix pass ? 12 November 2026

Branch: fix/audit-fixes. **Partial remediation: 10 fixed; 27 remain open or verification-blocked.** Original audit observations above are historical, not new reproduction evidence. Every Fixed item has a failing-before/passing-after regression and a safe-suite rerun. Deferred items were not all reproduced again; they must not be treated as closed. The four Not reproducible labels mean verification is blocked by unavailable PostgreSQL or the prohibition on data-altering migrations, not that the report was disproved.

### Summary

| Status | High | Medium | Low | Total |
| --- | --- | --- | --- | --- |
| Fixed | 2 | 5 | 3 | 10 |
| Not reproducible | 3 | 1 | 0 | 4 |
| Needs human decision | 3 | 18 | 2 | 23 |

No Critical findings in the original report. No finding is marked Won't fix.

### Needs human decision

- **BUG-003:** Verification blocked, not a false-positive determination. PostgreSQL is unavailable; integer/boolean failure cannot be re-run. Existing migration is applied history: choose a reviewed release/repair strategy rather than editing it blindly. Recommend disposable PostgreSQL verification before any deployment.
- **BUG-004:** Verification blocked, not a false-positive determination. Reproduction requires executing the existing data-altering migration, prohibited for this task. Recommend a reviewed forward-only repair migration; choose whether legacy completion is grandfathered or revalidated.
- **BUG-005:** Verification blocked, not a false-positive determination. Destructive downgrade reproduction is expressly prohibited. Do not interpret this as a false positive. Recommend a guard refusing incompatible downgrade; backup/export and rollback policy need approval.
- **BUG-006:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose deployed gateway/shared-store rate limiting versus application enforcement. Recommend deployment-level IP/account limits with a shared backend; process-local counters alone are bypassable across workers. New 429/retry behavior and thresholds require client review.
- **BUG-007:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Demo deployment settings are deliberate prototype policy, not evidence of an exposed production deployment. Choose separate production Compose or strict startup environment mode. Recommend private DB networking, required environment credentials, secure cookies, no demo/seeding in production.
- **BUG-008:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. An early streaming body/auth guard must cover chunked bodies, multipart overhead, reverse proxy limits and all worker paths. Choose gateway limits plus application streaming cap; recommend both. Requires reviewed size/status contract (413 versus existing 409/401), not just a Content-Length check.
- **BUG-009:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Existing tests intentionally apply with incomplete onboarding. Choose grandfathered applications versus enforced completion for new applications. Recommend enforce completion after BUG-010; requires coordinated client denial/status behavior.
- **BUG-010:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose step invalidation policy after edits/deletion, including resetting later steps and grandfathered completed candidates. Recommend invalidate from the earliest currently invalid required step. This changes completion/gating behavior and needs coordinated client review.
- **BUG-012:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Global roles are explicitly approved architecture. Choose restricting global role edits to platform authority versus agency-scoped capabilities. Recommend restrict global changes first; do not silently introduce a new role model.
- **BUG-014:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose successor requirement versus platform recovery path. Recommend preventing final-supervisor demotion with a reviewed conflict response, including concurrent demotions and other-agency effects.
- **BUG-015:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose revoking outstanding referrals versus reassigning their future candidates when staff leave. Recommend fail-closed signup until an active referrer is designated, with transactional recheck and client-visible explanation.
- **BUG-016:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose resolver status/reason for suspended agencies within the existing status enum. Recommend valid:false plus a reason without treating temporary suspension as token revocation; coordinate with BUG-015/017.
- **BUG-017:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose default fallback to another active agency versus explicit agency selection/denial. Recommend explicit eligibility checks and a documented denial response; do not silently change 200 login behavior for multi-agency clients.
- **BUG-018:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Requires translating uniqueness conflicts with transaction rollback across registration, applications, staff creation and team creation. Recommend targeted constraint mapping and deterministic PostgreSQL competing-transaction tests; coordinate newly controlled 409 behavior instead of current 500.
- **BUG-019:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Filesystem and database cannot share one atomic transaction. Choose staging/compensation versus durable pending-deletion metadata/reconciliation. Recommend staged uploads plus retryable tombstones; broader schema/storage failure handling needs review.
- **BUG-020:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose document structural validation and malware policy. Recommend bounded parser-based validation; ZIP signature checks do not validate DOCX and a four-byte PDF check is insufficient. Dependency and accepted-file compatibility review required.
- **BUG-021:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose display-name limit and extension policy/status. Recommend deriving disk extensions from validated MIME/structure and a bounded display filename; review new validation rejection with clients and both OS paths.
- **BUG-022:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose normalization/password whitespace and required-field policy. Recommend normalize human text before validation, preserve password bytes, reject blank required job/academic fields. Tightened schemas/status behavior needs client review.
- **BUG-023:** Verification blocked, not a false-positive determination. PostgreSQL VARCHAR enforcement cannot be reproduced locally. Recommend bounded derived activity messages versus a reviewed column-widening migration. Never apply an unverified data-altering migration.
- **BUG-024:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose per-tag and aggregate sizes. Recommend short tags and a total JSON body limit; reject rather than silently truncate, with client validation/status review.
- **BUG-025:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose per-candidate count/byte quotas and replacement/deletion policy. Recommend atomic aggregate quota enforcement, with storage ownership and capacity policy approved first.
- **BUG-026:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Pagination/filtering and narrower mutation responses change the shared web/mobile contract. Recommend additive bounded resource endpoints and staged client migration; retain existing routes until conversion is verified.
- **BUG-028:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Requires reviewed additive index migration and canonical PostgreSQL query plans. Recommend tenant/time and user/revocation indexes driven by actual workloads; do not alter applied migrations or apply schema changes here.
- **BUG-031:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose session retention/audit requirements and scheduled cleanup ownership. Recommend bounded expiration/revocation cleanup with supporting indexes. No deletion of existing session data is authorized in this task.
- **BUG-032:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Choose stable child-record update semantics versus documented replace-all. Recommend ID-aware ownership-checked reconciliation; review removed/unknown IDs and stale concurrent autosaves before changing collection lifecycle.
- **BUG-035:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Constant health is valid liveness rather than a reproduced auth/functional exploit. Choose an additive readiness endpoint and deployment healthcheck. Recommend separate readiness; adding a route requires explicit contract review.
- **BUG-036:** Deferred on the contract/design grounds below; original audit reproduction was not rerun in this fix pass. Basic nosniff/frame/referrer protections were added with BUG-029. Docs CSP, TLS/HSTS and proxy responsibilities remain unverified. Recommend docs-compatible CSP and HSTS only at the trusted HTTPS terminator; do not impose a guessed policy.

Client-visible security corrections already implemented: BUG-001 now denies candidate targets with the existing 403 shape; BUG-002 denies cross-agency jobs with existing 404 shape; BUG-033 rejects malformed CSRF tokens with 403 instead of an unhandled 500. Routes and JSON request/response schemas are unchanged. BUG-037 corrects OpenAPI binary media metadata; generated-client consumers should review regeneration. Confirm client handling of these denials before deployment.

### New env vars / config / migrations required before deploy

- No new dependencies, environment variables, hardcoded credentials, or applied/authored migrations. The dummy password hash is generated from a random value at process startup.
- No production credentials or .env contents inspected; no existing DB used. Every test used the conftest-created OS-temporary SQLite database and documents; the runner disposed engines and removed generated data afterward.
- Review existing COOKIE_SECURE, DEMO_LOGIN_ENABLED, SEED_ON_STARTUP, CORS_ORIGINS and database networking before a real deployment (BUG-007). Rate limiting, upload limits, quotas, retention, index and data-repair migration policies remain pending above.

### Verification and anything still unverified

- Per-group safe-suite reruns: 30, 32, 33, 34, 35, 37, 38, 40 and 41 passing tests. Final permitted suite: **44 passed in 52.74 seconds**; Ruff and git diff --check passed. Focused High-fix replay plus bursts: **7 passed in 9.14 seconds**. Existing tests/test_migrations.py was excluded because it executes downgrade/drop operations prohibited by this task. No failed implementation was committed.
- Regression tests rerun the original staff-target, deactivation, cross-agency apply, missing-cache-header, malformed-CSRF, unknown-login hashing, N+1, partial-save, binary-contract and upload-thread scenarios. All Fixed claims depend on passing replays; deferred items require separate reproduction before implementation.
- Bounded main-route burst: 16 requests at 4 workers per route, all 200. Median/p95: jobs 104.59/187.17 ms; staff 157.39/261.02 ms; platform 92.28/126.55 ms. These in-process SQLite measurements are not directly comparable to the original eight-worker run and do not prove production throughput or absence of performance regressions at larger scale.
- PostgreSQL, deployed proxy/browser/TLS behavior, distributed throttling, migration repair/downgrade, destructive fault/load scenarios and production deployment remain unverified. No production access was attempted. This branch is not a declaration that the platform is production-secure.
