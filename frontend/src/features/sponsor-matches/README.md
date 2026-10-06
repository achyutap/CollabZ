# sponsor-matches (CollabZ v2)
Route: `/sponsor/problems/[id]/matches` (RoleGuard sponsor).
API: GET /problems/{id}, GET /problems/{id}/requests (poll 10s), GET /problems/{id}/matches, POST /problems/{id}/requests {researcher_ids}, GET /projects/{id} (to tag Lead/Researcher).
Notes: multi-researcher flow; invites allowed while problem is open or matched; matches already exclude requested researchers (server side); no expired messaging.
## Contract gaps
- ResearcherRequestOut has no lead/co flag; Lead/Researcher tag is read from ProjectDetail.researchers.
