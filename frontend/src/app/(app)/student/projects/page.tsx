"use client";
import { RoleGuard } from "@/lib/auth";
import ProjectsListPage from "@/features/student-requests/ProjectsListPage";

export default function Page() {
  return (
    <RoleGuard roles={["student"]}>
      <ProjectsListPage role="student" />
    </RoleGuard>
  );
}
