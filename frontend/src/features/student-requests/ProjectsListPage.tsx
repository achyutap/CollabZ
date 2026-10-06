"use client";
import { useState } from "react";
import Link from "next/link";
import { FolderKanban } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import type { ProjectOut } from "@/lib/types";
import { StatusBadge, EmptyState, PageHeader, Spinner } from "@/components/common";
import { formatDate } from "@/components/common/format";
import { useErrorToast } from "./util";

type Role = "sponsor" | "researcher" | "student";
type Filter = "all" | "active" | "completed";

const EMPTY: Record<Role, { title: string; description: string; href: string; cta: string }> = {
  sponsor: { title: "No projects yet", description: "Projects appear once a researcher accepts your problem.", href: "/sponsor/problems", cta: "View problems" },
  researcher: { title: "No projects yet", description: "Accept a sponsor request to start leading or joining a project.", href: "/researcher/requests", cta: "View requests" },
  student: { title: "No projects yet", description: "Accept a request from a researcher to join your first project.", href: "/student/requests", cta: "View requests" },
};

function researchersLabel(p: ProjectOut): string {
  const names = p.researchers.length > 0 ? p.researchers.map((r) => r.name) : [p.researcher.name];
  return names.length > 1 ? `${names[0]} +${names.length - 1}` : names[0];
}

export default function ProjectsListPage({ role }: { role: Role }) {
  const { data, error, loading } = useFetch<ProjectOut[]>("/projects");
  useErrorToast(error);
  const [filter, setFilter] = useState<Filter>("all");
  const list = (data ?? []).filter((p) => filter === "all" || p.status === filter);
  const e = EMPTY[role];
  const chips: { id: Filter; label: string }[] = [{ id: "all", label: "All" }, { id: "active", label: "Active" }, { id: "completed", label: "Completed" }];

  return (
    <div className="page">
      <PageHeader title="Projects" description="Everything you are part of on CollabZ." />
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter projects">
        {chips.map((c) => (
          <button key={c.id} type="button" aria-pressed={filter === c.id} onClick={() => setFilter(c.id)} className={`badge cursor-pointer px-3 py-1 ${filter === c.id ? "bg-indigo-600 text-white" : ""}`}>{c.label}</button>
        ))}
      </div>
      {loading && !data ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : list.length === 0 ? (
        <EmptyState
          title={data && data.length > 0 ? "No projects match this filter" : e.title}
          description={data && data.length > 0 ? "Try a different filter." : e.description}
          icon={<FolderKanban className="h-8 w-8" aria-hidden />}
          action={data && data.length > 0 ? undefined : <Link href={e.href} className="btn btn-primary">{e.cta}</Link>}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {list.map((p) => (
            <div key={p.id} className="card card-hover space-y-3 p-5">
              <Link href={`/projects/${p.id}`} className="block space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <h2 className="font-semibold text-slate-900">{p.title}</h2>
                  <StatusBadge status={p.status} />
                </div>
                <p className="muted text-sm">Researchers: {researchersLabel(p)} · Sponsor: {p.sponsor_name}</p>
                <p className="muted text-xs">{p.member_count} student{p.member_count === 1 ? "" : "s"} · {formatDate(p.created_at)}</p>
              </Link>
              {role === "researcher" && p.status === "active" && p.member_count === 0 && (
                <Link href={`/researcher/projects/${p.id}/team`} className="btn btn-secondary btn-sm">Build team</Link>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
