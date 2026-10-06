# CollabZ project workspace (Account 7, v2)

Route: `/projects/[id]` (`page.tsx` unchanged from v1, wraps `ProjectPage` in `Suspense`).
Tabs (`?tab=`, plus `?member=<id>` on Team): Overview, Team, Work, Files, Timeline, Assistant, Budget (labelled "Payout" once completed).
Everyone (sponsor, researchers, students) sees Work, Files, Timeline and Budget; the sponsor is read-only.

## API calls

| Area | Calls |
| --- | --- |
| Page | `GET /projects/{id}`, `GET /projects/{id}/counts` (15s), `GET /projects/{id}/submissions` (15s, header stats), `GET /projects/{id}/files` |
| Overview | `GET /projects/{id}/activity?limit=5` |
| Team / member view | `GET /projects/{id}/activity?user_id=&limit=100`, `GET /projects/{id}/submissions?student_id=`, `GET /projects/{id}/files` (filtered by `author_id`) |
| Work | `GET /projects/{id}/submissions` (15s), `POST /projects/{id}/submissions` (multipart: commit_msg, description, files, paths), `POST /submissions/{id}/review` {approve, feedback, public_file_ids} |
| Files | `GET /projects/{id}/files`, `GET /files/{id}/content`, `GET /files/{id}/versions`, `GET /files/{id}/download` (api.download), `PATCH /files/{id}/visibility`, `POST /projects/{id}/files/visibility` |
| Timeline | `GET /projects/{id}/activity?user_id=&limit=100` (15s) |
| Budget / Payout | `GET /projects/{id}/submissions?status=pending`, `POST /projects/{id}/complete`, `GET /projects/{id}/payout` |
| Assistant | `GET /projects/{id}/chat`, `POST /projects/{id}/chat` |

Links out: `/researcher/projects/[id]/team` (Manage team, when `can_manage`), `/profile/[id]` (member view).

## Behaviour notes

- No similarity score or percentage is shown anywhere; only the Original / Copied badge.
- First-offence warning banner after upload; `403 BLACKLISTED` shows a full-screen blocked notice with logout.
- Only the lead sees "Complete project"; co-researchers see an info note.
- Feed filters (person, status) are applied client-side to the polled list, since everyone sees everything.

## Contract gaps

- `PayoutOut.students[].impact` is shown in the "Quality %" column (no separate quality field exists). Values <= 1 are treated as fractions.
- `ai_quality_score` scale is unstated: values <= 1 are fractions, larger values are 0-100.
- "Days active" is counted from `created_at` to today (no completion date in `ProjectDetail`).
- Removed students are not in `members`, so their member view falls back to names from submissions/activity.
- Not compiled with `tsc`: shared modules come from Account 5.
