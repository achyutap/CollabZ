"use client";
import Link from "next/link";
import { Plus, FileText } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import type { ProblemOut, ProjectOut } from "@/lib/types";
import { StatusBadge, SkillChip, MoneyText, EmptyState, PageHeader, Spinner } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import { formatDate } from "@/components/common/format";
import { inr, useErrorToast } from "./util";

export default function ProblemsList() {
  const problems = useFetch<ProblemOut[]>("/problems");
  const projects = useFetch<ProjectOut[]>("/projects");
  useErrorToast(problems.error);

  function hrefFor(p: ProblemOut): string {
    if (p.status === "open") return `/sponsor/problems/${p.id}/matches`;
    const proj = projects.data?.find((x) => x.problem_id === p.id);
    return proj ? `/projects/${proj.id}` : `/sponsor/problems/${p.id}/matches`;
  }

  const newBtn = (
    <Link href="/sponsor/problems/new" className="btn btn-primary">
      <Plus className="h-4 w-4" aria-hidden /> New problem
    </Link>
  );

  return (
    <div className="page">
      <PageHeader title="Your problems" description="Problems you have funded on CollabZ." actions={newBtn} />
      {problems.loading && !problems.data ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : !problems.data || problems.data.length === 0 ? (
        <EmptyState
          title="Post your first problem"
          description="Describe a problem, set a budget and we will match you with researchers."
          icon={<FileText className="h-8 w-8" aria-hidden />}
          action={newBtn}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {problems.data.map((p) => (
            <Link key={p.id} href={hrefFor(p)} className="card card-hover block space-y-3 p-5">
              <div className="flex items-start justify-between gap-3">
                <h2 className="font-semibold text-slate-900">{p.title}</h2>
                <StatusBadge status={p.status} />
              </div>
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
                <MoneyText amount={p.budget} className="text-lg font-semibold" />
                <span className="muted">total budget</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-xl bg-indigo-50 p-2"><div className="muted">Students ({p.student_pct}%)</div><div className="font-medium">{inr((p.budget * p.student_pct) / 100)}</div></div>
                <div className="rounded-xl bg-emerald-50 p-2"><div className="muted">Researchers ({p.researcher_pct}%)</div><div className="font-medium">{inr((p.budget * p.researcher_pct) / 100)}</div></div>
                <div className="rounded-xl bg-amber-50 p-2"><div className="muted">Project fund ({p.project_pct}%)</div><div className="font-medium">{inr((p.budget * p.project_pct) / 100)}</div></div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {p.required_skills.map((s) => <SkillChip key={s} label={skillLabel(s)} />)}
              </div>
              <p className="muted text-xs">Posted {formatDate(p.created_at)}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
