"use client";
import { RoleGuard } from "@/lib/auth";
import TeamBuilder from "@/features/team-builder/TeamBuilder";

export default function Page({ params }: { params: { id: string } }) {
  return (
    <RoleGuard roles={["researcher"]}>
      <TeamBuilder projectId={params.id} />
    </RoleGuard>
  );
}
