"use client";

import { EmptyState, SkillChip, Spinner, Timeline } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import { useFetch } from "@/lib/hooks";
import type { ActivityItem } from "@/lib/types";
import type { TabProps } from "./components/tabTypes";
import { useErrorToast } from "./components/hooks";

export default function OverviewTab({ projectId, project, onOpenMember }: TabProps) {
  const activity = useFetch<ActivityItem[]>(`/projects/${projectId}/activity`, { params: { limit: "5" } });
  useErrorToast(activity.error);
  const skills = project.problem.required_skills;

  return (
    <div className="space-y-6">
      <section className="card">
        <h2 className="section-title">Problem</h2>
        <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-700">{project.problem.description}</p>
        <div className="divider my-4" />
        <h3 className="label">Required skills</h3>
        {skills.length === 0 ? (
          <p className="muted">No required skills listed.</p>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            {skills.map((s) => (
              <SkillChip key={s} label={skillLabel(s)} />
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <h2 className="section-title">Team progress</h2>
        {project.skill_needs.length === 0 ? (
          <div className="mt-3">
            <EmptyState title="No team needs defined yet" description="Researchers haven't listed how many students are needed per skill." />
          </div>
        ) : (
          <ul className="mt-4 space-y-4">
            {project.skill_needs.map((n) => {
              const pct = n.count > 0 ? Math.min(100, (n.filled / n.count) * 100) : 0;
              return (
                <li key={n.skill}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-800">{skillLabel(n.skill)}</span>
                    <span className="muted">{n.filled} / {n.count} filled</span>
                  </div>
                  <div
                    className="h-2 w-full overflow-hidden rounded-full bg-slate-100"
                    role="progressbar"
                    aria-label={`${skillLabel(n.skill)} positions filled`}
                    aria-valuemin={0}
                    aria-valuemax={n.count}
                    aria-valuenow={n.filled}
                  >
                    <div className={n.filled >= n.count ? "h-full bg-emerald-500" : "h-full bg-indigo-500"} style={{ width: `${pct}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="card">
        <h2 className="section-title">Recent activity</h2>
        <div className="mt-3">
          {activity.loading && !activity.data ? (
            <Spinner />
          ) : (
            <Timeline items={(activity.data ?? []).slice(0, 5)} onActorClick={onOpenMember} emptyText="Nothing has happened yet." />
          )}
        </div>
      </section>
    </div>
  );
}
