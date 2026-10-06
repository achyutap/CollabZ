"use client";

import { useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FolderX, Settings2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/hooks";
import type { FileOut, ProjectCounts, ProjectDetail, SubmissionOut } from "@/lib/types";
import { EmptyState, Spinner, StatusBadge, Tabs, UserAvatar } from "@/components/common";
import OverviewTab from "./OverviewTab";
import TeamTab from "./TeamTab";
import WorkTab from "./WorkTab";
import FilesTab from "./FilesTab";
import TimelineTab from "./TimelineTab";
import AssistantTab from "./AssistantTab";
import BudgetTab from "./BudgetTab";
import BlockedNotice from "./components/BlockedNotice";
import { useErrorToast } from "./components/hooks";

const TAB_IDS = ["overview", "team", "work", "files", "timeline", "assistant", "budget"] as const;
type TabId = (typeof TAB_IDS)[number];

function Quick({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2">
      <p className="text-base font-semibold text-slate-900">{value}</p>
      <p className="help">{label}</p>
    </div>
  );
}

export default function ProjectPage({ projectId }: { projectId: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const { data: project, error, loading, refetch } = useFetch<ProjectDetail>(`/projects/${projectId}`);
  const counts = useFetch<ProjectCounts>(`/projects/${projectId}/counts`, { intervalMs: 15000 });
  const subs = useFetch<SubmissionOut[]>(`/projects/${projectId}/submissions`, { intervalMs: 15000 });
  const files = useFetch<FileOut[]>(`/projects/${projectId}/files`);

  const blocked = error !== null && (error.status === 403 || error.status === 404);
  useErrorToast(error && !blocked ? error : null);

  const requested = searchParams.get("tab");
  const activeTab: TabId = (TAB_IDS as readonly string[]).includes(requested ?? "") ? (requested as TabId) : "overview";
  const memberId = searchParams.get("member");

  function update(mutate: (p: URLSearchParams) => void) {
    const params = new URLSearchParams(searchParams.toString());
    mutate(params);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  const tabs = useMemo(() => {
    const myRole = project?.my_role;
    const workCount =
      myRole === "lead" || myRole === "researcher"
        ? counts.data?.pending_approvals
        : myRole === "student"
        ? counts.data?.my_pending_submissions
        : undefined;
    return [
      { id: "overview", label: "Overview" },
      { id: "team", label: "Team" },
      { id: "work", label: "Work", count: workCount },
      { id: "files", label: "Files" },
      { id: "timeline", label: "Timeline" },
      { id: "assistant", label: "Assistant" },
      { id: "budget", label: project?.status === "completed" ? "Payout" : "Budget" },
    ];
  }, [project?.my_role, project?.status, counts.data]);

  if (error?.code === "BLACKLISTED") return <BlockedNotice />;

  if (!user || (loading && !project)) {
    return (
      <div className="flex justify-center py-16"><Spinner /></div>
    );
  }

  if (!project) {
    return (
      <div className="page">
        <EmptyState
          icon={<FolderX className="h-8 w-8" />}
          title={blocked ? "Project not available" : "Could not load project"}
          description={blocked ? "This project doesn't exist or you don't have access to it." : error?.detail ?? "Please try again in a moment."}
          action={<button type="button" onClick={() => void refetch()} className="btn btn-primary">Retry</button>}
        />
      </div>
    );
  }

  const submissions = subs.data ?? [];
  const approved = submissions.filter((s) => s.status === "approved").length;
  const days = Math.max(1, Math.ceil((Date.now() - new Date(project.created_at).getTime()) / 86400000));

  const tabProps = {
    projectId,
    role: user.role,
    project,
    onChanged: refetch,
    counts: counts.data,
    refreshCounts: counts.refetch,
    onOpenMember: (id: string) =>
      update((p) => {
        p.set("tab", "team");
        p.set("member", id);
      }),
  };

  return (
    <div className="page">
      <header className="card space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="break-words text-xl font-semibold text-slate-900 sm:text-2xl">{project.title}</h1>
              <StatusBadge status={project.status} />
            </div>
            <p className="muted">
              Sponsor: <span className="font-medium text-slate-700">{project.sponsor_name}</span>
              <span className="mx-2 text-slate-300">|</span>
              {project.member_count} {project.member_count === 1 ? "student" : "students"}
            </p>
            <ul className="flex flex-wrap gap-3">
              {project.researchers.map((r) => (
                <li key={r.id} className="flex items-center gap-2 text-sm text-slate-700">
                  <UserAvatar name={r.name} size="sm" />
                  {r.name}
                  {r.role === "lead" && <span className="badge bg-indigo-50 text-indigo-700">Lead</span>}
                </li>
              ))}
            </ul>
          </div>
          {project.can_manage && (
            <Link href={`/researcher/projects/${projectId}/team`} className="btn btn-primary">
              <Settings2 className="h-4 w-4" aria-hidden="true" />
              Manage team
            </Link>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Quick label="Approved / total submissions" value={`${approved} / ${submissions.length}`} />
          <Quick label="Files" value={String((files.data ?? []).length)} />
          <Quick label="Days active" value={String(days)} />
          <Quick label="Students" value={String(project.member_count)} />
        </div>
      </header>

      <div className="overflow-x-auto">
        <Tabs
          tabs={tabs}
          active={activeTab}
          onChange={(id) =>
            update((p) => {
              p.set("tab", id);
              p.delete("member");
            })
          }
        />
      </div>

      <div role="tabpanel" id={`panel-${activeTab}`}>
        {activeTab === "overview" && <OverviewTab {...tabProps} />}
        {activeTab === "team" && (
          <TeamTab
            {...tabProps}
            memberId={memberId}
            onCloseMember={() => update((p) => p.delete("member"))}
          />
        )}
        {activeTab === "work" && <WorkTab {...tabProps} />}
        {activeTab === "files" && <FilesTab {...tabProps} />}
        {activeTab === "timeline" && <TimelineTab {...tabProps} />}
        {activeTab === "assistant" && <AssistantTab {...tabProps} />}
        {activeTab === "budget" && <BudgetTab {...tabProps} />}
      </div>
    </div>
  );
}
