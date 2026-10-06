# Account 3 — backend money modules (v2)

Modules: `submissions` (files, originality, enforcement, review), `completion` (pure formulas in
`completion/formulas.py`), `plagiarism` (repurposed: only `GET /projects/{id}/integrity` and `GET /me/integrity`).
Delete `backend/data/app.db` before testing. Tests: `pytest app/modules/submissions app/modules/completion app/modules/plagiarism`.

## Contract gaps
- `requirements.txt` (Account 1) must include `python-multipart`, `pypdf`, `python-docx`, `httpx`.
- `create_access_token` signature is unspecified; tests try `(user_id, role)` then `({"sub","role"})`. Tests insert rows with
  named columns against the v2 schema and could not be executed in my sandbox (no FastAPI installed) — only compile-checked.
- Student stats at completion use the student's ORIGINAL submissions of every status (so rejections lower approval_ratio);
  copied submissions are excluded entirely. `files_count` = files of approved original submissions.
- Pending submissions of blacklisted members do not block completion; all others do.
- Zero-amount payouts / zero project_fund write no ledger row (rewards rows are still written).
- Researcher pool: any NULL share_pct -> equal split; remainder goes to the lead. Displayed equal share = round(100/n, 2).
- Blocked upload: bytes are never written (the decision is made before `save_file`), so nothing needs deleting.
- Integrity events for a block are recorded once, against the project of the offending upload; `GET /projects/{id}/integrity`
  therefore lists it only there (other affected projects get notifications).
- POST /submissions also accepts `application/x-www-form-urlencoded` (no files). Review does not auto-block copied submissions
  from being approved; their files simply cannot be published.
- GET payout for removed students is allowed; blacklisted students get 403.
