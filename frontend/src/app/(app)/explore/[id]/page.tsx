"use client";
import PublicProjectPage from "@/features/profile/PublicProjectPage";

export default function Page({ params }: { params: { id: string } }) {
  return <PublicProjectPage projectId={params.id} />;
}
