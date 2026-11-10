# Product context

**Updated:** 30 October 2026  
**Architecture:** v0.2 approved by the owner.  
**Implementation:** existing frontend/backend reportedly run; source files were not supplied for this handoff.

## Purpose

Job Finder helps candidates and agency staff manage job-search work. The product direction includes candidate profiles, staff/team management, jobs, applications, and supervisor oversight. This is the discussed feature inventory, not an approved first release.

## Fixed decisions

- Two independent repositories in one workspace: `frontend/` and `backend/`.
- One Next.js frontend; thin routes and feature folders. Candidate, staff, and platform route areas; employees and supervisors share staff presentation.
- FastAPI with four concern folders: controllers, services, models, schemas. Services own database operations; no repositories or nested feature modules.
- Browser data through React Query and one Axios client. Authenticated server prefetching is deferred until a specific page requires it.
- One user identity system; agency memberships and backend permissions control access.
- API/PostgreSQL Compose setup and private local upload storage initially. No extra services without an actual feature need.
- Short agent tasks with explicit scope, acceptance criteria, and truthful verification.

## Open decisions

| Decision | When it is needed |
| --- | --- |
| First product milestone: UI review or real working flow | Before feature implementation |
| First included features and their order | With that milestone |
| Role capabilities, agency membership rules, onboarding/approval states | Before auth/onboarding contracts and migrations |
| Session lifecycle, CSRF mechanism, endpoint contracts | Before authentication implementation |

Candidate onboarding/profile, employee/team CRUD, jobs CRUD, application tracking, and supervisor screens are candidate work items. Discovery, provider connections, inbox/calendar, browser extension/autofill, advanced reporting, and notifications remain later or mocked work only when explicitly assigned.

Do not interpret architecture approval as approval for every feature. The next executable handoff task is **T00: baseline audit**. No new feature decision is needed to inspect and document the working setup.
