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

## Flow 1 — Candidate onboarding, profile, and apply

1. Open `/demo` and choose **Aya Khan**.
2. On **Overview**, confirm profile strength is 70% and the next action is **Add your documents**.
3. Open **Onboarding**, upload a small PDF or DOCX, then finish onboarding.
4. Confirm progress reaches 100%, all three steps show **Complete**, and the overview next action changes to browsing roles.
5. Open **Profile**, change the headline, location, and skills, then save. Refresh and confirm the values persist.
6. Open **Open roles**, apply to an open role, then open **Applications**. Confirm the role appears as **Submitted**.
7. Return to the same role and confirm the apply action is no longer available.

**Expected:** progress and application state survive refresh; duplicate applications are rejected by the API.

## Flow 2 — Supervisor assignment and pipeline

1. Open `/demo` and choose **Noor Ahmed** (supervisor, Northstar).
2. On **Overview**, confirm the pipeline columns and the “needs an owner” count match the candidate directory.
3. Open **Candidates**, reassign an unassigned candidate to an employee, then change that candidate’s stage.
4. Confirm the overview counts and recent activity reflect both changes.
5. Open **Team**, create a member, copy the one-time temporary password, then change the member’s role/team and deactivate them.
6. Confirm you cannot deactivate your own supervisor account.
7. Open **Jobs**, publish a role, then close an existing role. Confirm the job board status updates.
8. Log in as the candidate and confirm a newly published role appears and a closed role cannot be applied to.

**Expected:** supervisors can assign, manage members, and write jobs; all changes are agency-scoped.

## Flow 3 — Employee application update, candidate sees it

1. Open `/demo` and choose **Sam Ali** (employee).
2. Open **Applications**, change an application from **Submitted** to **Interview**.
3. Confirm the employee cannot assign candidates, manage the team, or write jobs (buttons/actions are absent or denied).
4. Log in as Aya and open **Applications**. Confirm the same application now shows **Interview**.

**Expected:** the shared pipeline updates immediately; role restrictions remain enforced by the API, not just the UI.

## Flow 4 — Platform administration

1. Open `/demo` and choose **Jules Lee** (platform admin).
2. Confirm the overview shows agencies, users, integrations, health, and audit events.
3. Open **Agencies**, change an agency’s status, and confirm the audit log records it.
4. Open **Integrations** and confirm they are visibly marked as simulated.
5. Visit `/staff` directly and confirm access is denied.

**Expected:** platform admins have no agency workspace and cannot read agency candidate data.

## Flow 5 — Authentication and session behaviour

1. Try a wrong password on `/login`; confirm an inline error appears without leaving the page.
2. Sign in, then use the account menu → **Change password**. Confirm you are returned to the login screen.
3. Sign in with the new password, open a workspace, then sign out.
4. Press the browser Back button; confirm the workspace does not render and you are redirected to login.
5. While signed in, open a private workspace URL for the wrong role (for example candidate → `/staff`); confirm a denied/redirected state.

**Expected:** opaque cookie sessions, server-side authorization, no mock fallback.

## Flow 6 — Responsive, palette, and failure states

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
