"use client";
import { RoleGuard } from "@/lib/auth";
import ProjectsListPage from "@/features/student-requests/ProjectsListPage";

export default function Page() {
  return (
    <RoleGuard roles={["researcher"]}>
      <ProjectsListPage role="researcher" />
    </RoleGuard>
  );
}
