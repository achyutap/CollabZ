# student-requests (CollabZ v2)
Routes: `/student/requests` (RoleGuard student); `ProjectsListPage` used by `/sponsor/projects`, `/researcher/projects`, `/student/projects` (each wrapped in its RoleGuard).
API: GET /student/requests (poll 15s), POST /student-requests/{id}/respond {accept}, GET /projects.
Notes: tabs with counts; 409 on accept -> "Slots for this skill are full" + refetch; project list shows all researchers ("Dr A +1"), Active/Completed chips, "Build team" for researchers with active empty projects.
## Contract gaps
- none
