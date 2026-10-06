# team-builder (CollabZ v2)
Route: `/researcher/projects/[id]/team` ("Manage team", RoleGuard researcher).
API: GET /projects/{id}, POST /projects/{id}/skill-needs, GET /projects/{id}/shortlist (poll 10s), POST /projects/{id}/student-requests, GET /projects/{id}/student-search?q=&skill=, DELETE /projects/{id}/members/{student_id}, PUT /projects/{id}/researcher-shares.
Sections: Skills needed, Shortlist, Add any student, Current team (Remove), Researchers (lead edits shares, others read-only). Ratings are plain stars.
## Contract gaps
- none
