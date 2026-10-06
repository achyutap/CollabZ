"use client";
import { RoleGuard } from "@/lib/auth";
import StudentRequestsPage from "@/features/student-requests/StudentRequestsPage";

export default function Page() {
  return (
    <RoleGuard roles={["student"]}>
      <StudentRequestsPage />
    </RoleGuard>
  );
}
