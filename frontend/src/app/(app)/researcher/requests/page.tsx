"use client";
import { RoleGuard } from "@/lib/auth";
import ResearcherRequestsPage from "@/features/researcher-requests/ResearcherRequestsPage";

export default function Page() {
  return (
    <RoleGuard roles={["researcher"]}>
      <ResearcherRequestsPage />
    </RoleGuard>
  );
}
