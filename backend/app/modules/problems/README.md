# Account 2 backend flow v2: problems, researcher_match, projects, student_match

Routers expose `router = APIRouter()` with full contract paths; everything is synchronous. Multi-statement writes use `transaction(conn)`. Project access uses `app.core.access`; notifications/timeline use `app.core.notify`. Delete `backend/data/app.db` before testing (v2 schema). Tests: `cd backend && pytest app/modules/<name>/tests`.

## problems
- `POST /problems` [sponsor]: body adds `researcher_pct`, `project_pct` (defaults: project_pct=0, researcher_pct=100-student_pct-project_pct; sum must be 100 else 422). Escrows the budget, extracts skills.
- `GET /problems` [sponsor own; researcher: with a request for them; student 403]
- `GET /problems/{id}`: sponsor owner, researcher with a request on it, or any project researcher.
- `PATCH /problems/{id}/skills` [sponsor owner, open only]

## researcher_match
- `GET /problems/{id}/matches` [sponsor owner]: top 5; excludes researchers with any request for the problem or in its project.
- `POST /problems/{id}/requests` [sponsor owner]: problem open or matched (completed -> 400 BAD_STATE); notifies each researcher.
- `GET /problems/{id}/requests` [sponsor owner]; `GET /researcher/requests` [researcher]
- `POST /researcher-requests/{id}/respond`: accept creates the project (lead) or adds a co-researcher; no other request is expired; completed problem -> request expired + 409; decline notifies the sponsor.

## projects
- `GET /projects` (sponsor / project researcher / active student), `GET /projects/{id}` (ProjectDetail with researchers, shares, budget split, my_role, can_manage)
- `POST /projects/{id}/skill-needs` [any project researcher, active project]: replace if no student requests, else upsert; filled counts active members only.
- `DELETE /projects/{id}/members/{student_id}` [project researcher, active project]
- `PUT /projects/{id}/researcher-shares` [lead, active project]
- `GET /projects/{id}/counts` [project people]

## student_match
- `GET /projects/{id}/shortlist`, `GET /projects/{id}/student-search?q=&skill=`, `POST|GET /projects/{id}/student-requests` [project researchers]
- `GET /student/requests` [student]; `POST /student-requests/{id}/respond` [addressed student]: cap enforced inside a transaction; removed students are reactivated in place on re-accept.

## Contract gaps
- `create_access_token` signature unspecified; tests try `(user_id, role)` then a claims dict.
- 422 for malformed bodies relies on Account 1 mapping FastAPI validation errors to `VALIDATION_ERROR`.
- Effective researcher share: stored values when every researcher has one, otherwise equal split (remainder to lead). A co-researcher joining after the lead set shares therefore resets display to an equal split until the lead re-saves; Acc3's payout must use the same rule.
- Re-invite after decline/expire/removal reuses the existing `student_requests` row (UNIQUE constraint); only a pending request blocks a new one.
- Student lacking the verified skill -> 400 `VALIDATION_ERROR`; blacklisted student invite -> 400 `BAD_STATE`; unknown student -> 404.
- Student requests are not restricted to active projects (not stated in contract).
- Empty skill-needs array -> 422. Duplicate researcher_ids in one POST are de-duplicated.
- Removing a student leaves their old `accepted` request row as-is (only pending requests are expired).
- `StudentOut.pending_skills` is always `[]` in these modules (requesters are researchers).
- Researcher shares PUT and member removal require an active project (400 BAD_STATE otherwise).
