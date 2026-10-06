# researcher-requests (CollabZ v2)
Route: `/researcher/requests` (RoleGuard researcher).
API: GET /researcher/requests (poll 15s), POST /researcher-requests/{id}/respond {accept}.
Notes: tabs Pending (n) / Accepted / Other; accept -> /projects/[project_id] (page shows lead vs co-researcher via my_role); no 409 "taken" handling (generic toast of server detail).
## Contract gaps
- none
