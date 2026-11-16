# Manual testing — production prototype

Use this guide to verify the platform end to end before calling the build complete. It assumes both services are running locally:

```bash
# terminal 1 — backend
cd backend
uv run alembic upgrade head
uv run seed
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# terminal 2 — frontend
cd frontend
pnpm dev
```

Open `http://localhost:3000`. All demo accounts use the password **`Demo1234!`**.

| Role | Email |
| --- | --- |
| Candidate | `aya@demo.example.com` |
| Employee | `sam@demo.example.com` |
| Supervisor | `noor@demo.example.com` |
| Platform admin | `jules@demo.example.com` |

Seeded referral fixtures: `/join/northstar-referral-demo` (active, created by Sam Ali),
`harbor-referral-used` (used), and `northstar-referral-expired` (expired). Aya Khan is an
independent candidate with no agency membership and an unfinished onboarding flow, so she is the
fastest way to inspect the candidate gate.

## Flow 1 — Independent candidate signup and resumable onboarding

1. Open `/register`. Confirm the copy says independent candidates can browse every open role and
   join an agency later with a referral link.
2. Create a new account. Confirm you land on `/candidate/onboarding` in the **Account** step with
   no agency shown, and that every other workspace route redirects back to onboarding.
3. On **Personal**, type a phone, location, and headline but do not save. Reload the page and
   confirm the typed values are restored from the local draft.
4. Save and continue. Open **Professional**, add a title, skills, and one role with a start month,
   then save. Open **Academic**, add one qualification, then save.
5. Sign out, sign back in, and reopen onboarding. Confirm the completed steps are marked complete
   and the next incomplete step is open with its saved values.
6. Try to open a later step before the current one is complete; confirm it is locked (and the API
   rejects out-of-order completion).
7. Upload a small PDF or DOCX on **Documents**, then finish onboarding. Confirm progress reaches
   100%, all four server steps show **Complete**, and the review step offers **Browse open roles**.
8. Open **Open roles** and confirm roles from active agencies are listed. Apply to one, then open
   **Applications** and confirm the role, company, and agency appear as **Submitted**.
9. Return to the same role and confirm the apply action is no longer available.

**Expected:** the account has no agency; saved steps survive refresh and logout/login; unsaved
edits survive reload; duplicate applications are rejected by the API.

## Flow 2 — Referral signup from a single-use link

1. As Sam Ali (employee), open **Referrals** and create a link with a label and 7-day expiry.
2. Copy the one-time `/join/<token>` link. Confirm the full token is not shown again after you
   dismiss the notice.
3. In a private window, open the link. Confirm the agency and referrer are shown before signup.
4. Create the account. Confirm you land on onboarding, the Account step shows the referrer and
   agency, and the session belongs to the agency.
5. Open the link again in another private window and confirm signup is rejected as already used.
6. Confirm the seeded expired and used links (`northstar-referral-expired`,
   `harbor-referral-used`) resolve as invalid with a clear reason.

**Expected:** a link works exactly once; the candidate is assigned to the referrer; invalid links
offer the independent signup path without silently falling back.

## Flow 3 — Staff referral management

1. As Sam Ali (employee), open **Referrals**. Confirm only links created by Sam are listed, with
   active/used/expired status and expiry.
2. Revoke an active link. Confirm its status becomes **Revoked** and the link no longer resolves.
3. Confirm the employee cannot see or revoke another agency's links.
4. As Noor Ahmed (supervisor), switch between Northstar and Harbor and confirm the referral list
   changes with the active agency. Confirm a supervisor sees every link in the active agency.

**Expected:** referral management is agency-scoped and role-aware; revocation is immediate.

## Flow 4 — Supervisor assignment and pipeline

1. Open `/demo` and choose **Noor Ahmed** (supervisor, Northstar).
2. On **Overview**, confirm the pipeline columns and the “needs an owner” count match the candidate directory.
3. Open **Candidates**, reassign an unassigned candidate to an employee, then change that candidate’s stage.
4. Confirm the overview counts and recent activity reflect both changes.
5. Open **Team**, create a member, copy the one-time temporary password, then change the member’s role/team and deactivate them.
6. Confirm you cannot deactivate your own supervisor account.
7. Open **Jobs**, publish a role, then close an existing role. Confirm the job board status updates.
8. Log in as the candidate and confirm a newly published role appears and a closed role cannot be applied to.

**Expected:** supervisors can assign, manage members, and write jobs; all changes are agency-scoped.

## Flow 5 — Employee application update, candidate sees it

1. Open `/demo` and choose **Sam Ali** (employee).
2. Open **Applications**, change an application from **Submitted** to **Interview**.
3. Confirm the employee cannot assign candidates, manage the team, or write jobs (buttons/actions are absent or denied).
4. Log in as Aya and open **Applications**. Confirm the same application now shows **Interview**.

**Expected:** the shared pipeline updates immediately; role restrictions remain enforced by the API, not just the UI.

## Flow 6 — Platform administration

1. Open `/demo` and choose **Jules Lee** (platform admin).
2. Confirm the overview shows agencies, users, integrations, health, and audit events.
3. Open **Agencies**, change an agency’s status, and confirm the audit log records it.
4. Open **Integrations** and confirm they are visibly marked as simulated.
5. Visit `/staff` directly and confirm access is denied.

**Expected:** platform admins have no agency workspace and cannot read agency candidate data.

## Flow 7 — Authentication and session behaviour

1. Try a wrong password on `/login`; confirm an inline error appears without leaving the page.
2. Sign in, then use the account menu → **Change password**. Confirm you are returned to the login screen.
3. Sign in with the new password, open a workspace, then sign out.
4. Press the browser Back button; confirm the workspace does not render and you are redirected to login.
5. While signed in, open a private workspace URL for the wrong role (for example candidate → `/staff`); confirm a denied/redirected state.

**Expected:** opaque cookie sessions, server-side authorization, no mock fallback.

## Flow 8 — Responsive, palette, and failure states

1. At a 390px width, open the navigation drawer, switch pages, and confirm it closes.
2. On desktop, press **⌘K** / **Ctrl+K**, search for a page, and open it. Confirm Escape closes the palette.
3. Stop the backend, refresh a workspace page, and confirm an explicit “API is not reachable” state with a retry action. Confirm no mock data appears.
4. Restart the backend and use **Try again**.

**Expected:** the interface stays usable on mobile, keyboard navigation works, and API failures are visible rather than silently replaced.

For rendered system and workflow diagrams, see [FLOWS.md](FLOWS.md).

## Resetting the local demo

The local database is `backend/data/jobfinder.db`. To reset demo data, stop the API and delete that file, then run:

```bash
uv run alembic upgrade head
uv run seed
```

This is destructive and intended for the local prototype only. Never delete a shared or production database as a troubleshooting shortcut.
