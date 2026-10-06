import type { ProjectCounts, ProjectDetail, UserOut } from "@/lib/types";

export interface TabProps {
  projectId: string;
  role: UserOut["role"];
  project: ProjectDetail;
  /** Refetch the project detail. */
  onChanged: () => Promise<void>;
  counts: ProjectCounts | undefined;
  refreshCounts: () => Promise<void>;
  onOpenMember: (id: string) => void;
}

export function isProjectResearcher(p: ProjectDetail): boolean {
  return p.my_role === "lead" || p.my_role === "researcher";
}
