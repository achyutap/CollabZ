# Notifications (Account 5)

Route: `/notifications` (`src/app/(app)/notifications/page.tsx` -> `NotificationsView`).
The topbar bell (`NotificationBell`) lives in `(app)/layout.tsx`.

API calls: `GET /notifications?unread_only=`, `POST /notifications/{id}/read`, `POST /notifications/read-all`, `GET /me/counts` (via `useCounts`).
Clicking an item marks it read and navigates to `link` as-is.
