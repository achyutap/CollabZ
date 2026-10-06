# CollabZ frontend (Next.js 14 App Router)

## Run
```
cd frontend
cp .env.local.example .env.local
npm install
npm run dev      # http://localhost:3000
npm run typecheck
```
The backend must run at `NEXT_PUBLIC_API_URL` (default http://localhost:8000).
Demo logins (password `demo1234`): sponsor1@demo.com, researcher1@demo.com, student1@demo.com.

## Foundation (Account 5)
- `src/lib`: `api.ts`, `auth.tsx`, `hooks.ts`, `toast.tsx`, `types.ts`
- `src/components/common`: shared UI primitives (+ `skills.ts`)
- `src/app/(app)/layout.tsx`: auth guard, sidebar, topbar
- Pages: `/login`, `/register`, `/student/quiz`, `/student/profile` (see `src/features/quiz/README.md`)

## V2 notes
- Design system: see `DESIGN.md`; component showcase at `/dev/components`.
- Notifications: bell in the topbar + `/notifications` (`src/features/notifications`).
- Quiz: only pending skills; `/student/profile` redirects to `/profile`.

## Contract gaps
- Sidebar links to `/explore`, `/profile`, `/student/projects` etc. point at pages owned by other accounts.
- Student "Projects" sidebar item has no badge (v2 does not say which count it should show).
- A `403 BLACKLISTED` on any authenticated call clears the token, stores the message and redirects to `/login` (after 1.5 s so a toast can show), where a red panel displays it.
- `useAuth()` exposes `refreshUser()`; `ShortlistCandidate.rating_type` stays in `types.ts` but must never be rendered.
- `GET /students/{id}` access for self is assumed allowed (not needed by this account in v2).
