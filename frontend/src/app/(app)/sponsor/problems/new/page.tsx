"use client";
import { RoleGuard } from "@/lib/auth";
import NewProblemForm from "@/features/sponsor-problems/NewProblemForm";

export default function Page() {
  return (
    <RoleGuard roles={["sponsor"]}>
      <NewProblemForm />
    </RoleGuard>
  );
}
