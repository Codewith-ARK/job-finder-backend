# Feature tracker — one active feature at a time

**Purpose:** keep development moving in one direction. This is the governing document for
active work. Read it before starting any task, update it when work starts or finishes, and do
not begin the next feature until the active feature meets its definition of done.

## Operating rules

1. **One active feature.** Only one feature may be `Active`. Everything else is `Backlog`,
   `Blocked`, or `Done`.
2. **Complete before moving on.** Do not start a new feature, or pick up an unrelated
   improvement, while the active feature has unmet acceptance criteria. Record small follow-ups
   in the backlog instead of expanding the current feature.
3. **Waterfall within a feature.** Specify → implement → verify → record evidence → accept.
   Do not circle back to a finished feature unless verification found a defect.
4. **Scope changes are explicit.** If a new requirement appears, add it to the active feature's
   scope or the backlog, get owner approval, then implement. Do not silently expand scope.
5. **Evidence, not claims.** Record verified commands and results in the repository
   `CONTEXT.md`. Never mark a feature done while a check is unrun or a criterion is unmet.
6. **Docs follow code.** Update `PLAN.md`, `EXECUTION.md`, `FLOWS.md`, `MANUAL_TESTING.md`,
   `CONTEXT.md`, and the relevant `AGENTS.md` observed-conventions section before marking a
   feature done.

## Status board

| ID | Feature | Status | Contract | Evidence |
| --- | --- | --- | --- | --- |
| F01 | Candidate identity independence, referral links, and resumable onboarding | **Done** (12 Nov 2026) | `PLAN.md` § F01 | `CONTEXT.md` |
| F02 | Agency conversations and candidate job queue | Backlog (phase 2) | `PLAN.md` § F02 | — |
| F03 | Deployment hardening: secure cookies, demo/seed shutdown, PostgreSQL verification | Backlog | — | — |

## F01 — Candidate identity independence, referral links, and resumable onboarding

**Status:** Done — 12 November 2026. No other feature is active; F02 is the next candidate and stays backlog until the owner assigns it.

**Goal:** a candidate can join independently, or through a single-use agency referral link, and
then completes one resumable signup + onboarding flow. Candidate data is candidate-owned;
agency access is an explicit relationship created by referral or assignment.

### Scope

- `candidate_profiles.agency_id` becomes nullable. A candidate needs no agency; an agency
  employee/supervisor always needs an active agency membership.
- Referral links are created by agency employees/supervisors, expire after a configurable
  period, and are valid for exactly one successful signup.
- Referral signup creates the candidate account, agency membership, and assignment to the
  referring employee/supervisor in one transaction.
- Onboarding is part of signup, not a separate later page: Account → Personal → Professional →
  Academic → Documents → Review.
- In-progress onboarding is resumable across reload, logout, and login. The server stores saved
  step data; a Zustand store with `persist` keeps unsaved local edits and syncs them.
- Candidate profile data is normalized into logical tables: preferences, experiences,
  education, and skills. Transient form state does not become extra profile columns.
- Individual candidates see all open roles across active agencies; referred candidates see their
  agency's roles. Applications retain the job's agency for staff visibility.
- Candidate and agency UI keep separate feature boundaries and share only presentation
  primitives and explicit contracts.

### Out of scope

- F02 conversations, chat management, and the candidate job queue.
- Email delivery, OAuth, payments, real third-party integrations, and background workers.
- Realtime sockets, attachments in chat, or a full applicant-tracking system.

### Acceptance criteria

- [x] Individual registration succeeds with `session.agency = null`, no membership, and a
      candidate profile with `agency_id = null`.
- [x] A valid referral link shows the agency/referrer before signup, creates membership and
      assignment on success, and cannot be used a second time.
- [x] Expired, revoked, used, and unknown referral links are rejected with clear errors.
- [x] Employees and supervisors can create and revoke referral links in their active agency;
      employees cannot manage another agency's links.
- [x] Onboarding steps save partial data, resume after logout/login, enforce order, and only
      reach 100% when every required step is valid.
- [x] Personal, professional, academic, and document data are persisted in their normalized
      tables and returned by the candidate workspace.
- [x] Individual candidates can browse all open roles and apply; staff only see applications to
      their agency's jobs and cannot see independent candidates.
- [x] Referred candidates are visible to their agency and retain their assignment after login.
- [x] Backend tests cover individual/referral signup, single-use and expiry, resumable
      onboarding, authorization, and cross-agency denial.
- [x] Frontend checks (`lint`, `typecheck`, `test`, `build`) pass, and the Zustand draft survives
      a reload and a logout/login cycle.
- [x] Docs, migrations, seed data, and manual-testing flows describe the delivered behavior.

### Verification evidence

- Backend: `uv run ruff check .` clean; `uv run pytest -q` — 29 passed.
- Frontend: `pnpm lint` clean; `pnpm typecheck` clean; `pnpm test` — 7 passed; `pnpm build` —
  19 routes including `/join/[token]` and `/staff/referrals`.
- End-to-end HTTP smoke against a fresh migrated SQLite database (34/34 checks): individual
  signup with no agency, partial save, logout/login resume, ordered step completion, document
  upload, 100% completion, independent job browsing and application, single-use referral signup,
  used-link rejection, CSRF on referral creation, wrong-role denial, cross-agency revoke denial,
  staff visibility of referred but not independent candidates, and revoke.

### Task sequence

| Task | Status | Outcome |
| --- | --- | --- |
| F01.1 | Done | Normalized candidate model, nullable agency, referral table, migration |
| F01.2 | Done | Backend services/controllers, authorization, seed, focused tests |
| F01.3 | Done | Zustand onboarding store and unified signup/onboarding wizard |
| F01.4 | Done | Referral management UI, candidate gate, jobs/applications integration |
| F01.5 | Done | Full verification, mock/obsolete cleanup, documentation update |

## F02 — Agency conversations and candidate job queue (backlog)

**Status:** Backlog — do not start until F01 is accepted.

- One-to-one conversations between an assigned agent and candidate.
- Staff conversation list, unread/read state, close/archive, simple polling.
- Candidate visual job queue with clear application-status cues.
- No attachments or realtime sockets in the first slice.

Add the detailed contract here when F02 becomes active.
