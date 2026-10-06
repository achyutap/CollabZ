"use client";

import { Suspense } from "react";
import ProjectPage from "@/features/project/ProjectPage";
import { Spinner } from "@/components/common";

export default function ProjectRoutePage({ params }: { params: { id: string } }) {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      }
    >
      <ProjectPage projectId={params.id} />
    </Suspense>
  );
}
