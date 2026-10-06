"use client";
import { RoleGuard } from "@/lib/auth";
import MatchesPage from "@/features/sponsor-matches/MatchesPage";

export default function Page({ params }: { params: { id: string } }) {
  return (
    <RoleGuard roles={["sponsor"]}>
      <MatchesPage problemId={params.id} />
    </RoleGuard>
  );
}
