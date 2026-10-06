"use client";
import ProfileView from "@/features/profile/ProfileView";

export default function Page({ params }: { params: { id: string } }) {
  return <ProfileView userId={params.id} />;
}
