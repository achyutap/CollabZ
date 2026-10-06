"use client";
import { RoleGuard } from "@/lib/auth";
import ProblemsList from "@/features/sponsor-problems/ProblemsList";

export default function Page() {
  return (
    <RoleGuard roles={["sponsor"]}>
      <ProblemsList />
    </RoleGuard>
  );
}
