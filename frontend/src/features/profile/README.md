# profile + explore (CollabZ v2)
Routes: `/profile` (own, editable), `/profile/[id]`, `/explore`, `/explore/[id]`.
API: GET /me/profile, GET /users/{id}/profile, PATCH /me/profile (name, headline, about, location, links, details, add_skills, remove_skills), POST/DELETE /users/{id}/like, GET /me/wallet, GET /me/integrity, GET /explore/people?q=&role=, GET /explore/projects?q=&skill=, GET /explore/projects/{id}, GET /files/{id}/content, /files/{id}/versions, /files/{id}/download.
Notes: per-section edit/save; details are sent as the full merged object; students' new skills go pending (quiz link); researchers edit skills directly (>=1 kept); no budget shown on public pages.
## Contract gaps
- `details` PATCH semantics (replace vs merge) unspecified: the full merged object is sent.
- Year fields are sent as numbers when numeric (education start_year/end_year, publication year).
