# Quiz (Account 5, v2)

## Routes
- `/student/quiz` -> `QuizFlow` (SkillPicker -> QuestionView -> ReviewScreen -> QuizResults)
- `/student/profile` redirects to `/profile` (profile page is owned by another account)

## API calls
- `GET /quiz/skills` (pending skills only), `POST /quiz/start`, `POST /quiz/submit`, `GET /auth/me` (via `refreshUser()` after submit)

## Notes
- If no pending skills: EmptyState linking to `/profile`.
- Failed skills get a per-skill "Retake" button (starts a new attempt for just those skills).
- 30-minute countdown; auto-submits at zero. `INVALID_TOKEN` -> toast and restart.
- Rating is shown as plain stars with "Based on your quiz".
