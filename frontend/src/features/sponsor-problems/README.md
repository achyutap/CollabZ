# sponsor-problems (CollabZ v2)
Routes: `/sponsor/problems`, `/sponsor/problems/new` (RoleGuard sponsor).
API: GET /problems, GET /projects, GET /me/wallet, POST /problems {title, description, budget, student_pct, researcher_pct, project_pct}, PATCH /problems/{id}/skills.
Notes: three linked sliders/inputs always sum to 100 (changing one rebalances the others proportionally); mini DonutChart; INSUFFICIENT_FUNDS -> toast.
## Contract gaps
- v1 component files of this folder not listed in the v2 zip (if any) are superseded and unused; delete them if present.
