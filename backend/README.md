# CollabZ API (backend)

FastAPI + SQLite (stdlib sqlite3, synchronous).

## IMPORTANT (v2)
The schema changed and there are no migrations: **delete `backend/data/app.db` (and `backend/data/uploads/` if present) before running or testing.** `init_db()` recreates everything.

## Setup
```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run
```
uvicorn app.main:app --reload --port 8000
```
Run everything from the `backend/` directory. Tests: `pytest` (from `backend/`; set LLM_MOCK=true is done by the tests themselves).

## New core helpers (v2)
- `app.core.notify`: `notify`, `notify_many`, `log_event` (plain INSERTs; call inside your own `transaction(conn)`).
- `app.core.access`: `project_role`, `is_project_researcher`, `researcher_ids`, `lead_id`, `sponsor_id`, `active_student_ids`, `require_project_access`.
- `app.core.storage`: `save_file`, `read_file`, `delete_file`, `safe_path`, `is_text`, `decode_text`; files live in `UPLOAD_DIR/<project_id>/<file_id>`.
- `settings.upload_dir`, `max_file_bytes`, `max_files_per_submission`, `max_submission_bytes`.
- Blacklisted users get 403 `BLACKLISTED` from login and from every authenticated call (`get_current_user`).

## Notifications endpoints (module `app/modules/notifications`)
GET /notifications?unread_only=, POST /notifications/{id}/read, POST /notifications/read-all, GET /me/counts

## Auth endpoints (module `app/modules/auth`)
- POST /auth/register, POST /auth/login, GET /auth/me
- GET /researchers/{id}, GET /students/{id}
- GET /me/wallet
- GET /health

## How modules auto-register
`app/main.py` scans `app/modules/*` with pkgutil. Any package containing `router.py` that exposes `router = APIRouter()` is included automatically (no prefix; routers declare full contract paths). Import errors are logged with a traceback and skipped.

## Seeding
On startup, if `AUTO_SEED` is not `false` and the `users` table is empty, `seed.seed.run()` is called (written by another account). If `backend/seed/seed.py` does not exist, nothing happens. Set `AUTO_SEED=false` to disable. The DB lives at `DB_PATH` (default `backend/data/app.db`).

## Core API notes
`app.core.db`, `deps`, `errors`, `security`, `llm`, `embeddings`, `skills`, `config` match the shared contract. `get_conn()` reads `DB_PATH` at call time. `decode_token` gives 401 UNAUTHORIZED; `verify_payload` gives 400 INVALID_TOKEN.

## Contract gaps
- Unknown HTTP statuses without a contract code (e.g. 405) return code `HTTP_ERROR`.
- Student `skills` at registration now become `pending_skills` (invalid ids dropped, deduped); researcher bio is optional.
- Researcher skills not in the taxonomy are silently dropped; registration fails only if none remain.
- Emails are stored lowercase.
