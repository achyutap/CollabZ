# Account 4 (v2): quiz, assistant, files, activity, profiles, explore, seed

Run the seed from `backend/`: `python -m seed.seed` (delete `backend/data/app.db` first after the v2 schema change).

**Cleanup needed on merge:** delete the old `backend/seed/test_seed.py` from v1 (the only seed test now lives in `backend/seed/tests/test_seed.py`).

## Contract gaps
- Seed payout numbers use `impact = approved * approval_ratio` and `share_pct = impact / sum(impact)`; `project_ratings.score` and the students' `final_rating` are fixed demo values. The real formulas belong to Account 3, so recompute if it differs.
- The v2 contract does not say who receives the `project_fund` ledger entry. The seed credits it to the lead researcher's wallet.
- Backdated timestamps in the seed (events, notifications) are plain INSERTs, because `core.notify` helpers always stamp `now()`.
- Seed leaves `researcher_amount`-style data out; payout is reconstructed from `rewards`, `project_researchers.share_pct` and `ledger_entries`.
- `GET /explore/people` includes sponsors (the contract lists `role` without restricting it).
- Profile `location` is capped at 200 characters (the contract gives no limit).
