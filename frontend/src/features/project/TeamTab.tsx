"use client";

import { useMemo } from "react";
import { Users } from "lucide-react";
import { EmptyState, SkillChip, StarRating, UserAvatar } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import type { TabProps } from "./components/tabTypes";
import MemberView from "./components/MemberView";

export default function TeamTab(props: TabProps & { memberId: string | null; onCloseMember: () => void }) {
  const { project, projectId, memberId, onCloseMember, onOpenMember } = props;

  const groups = useMemo(() => {
    const order: string[] = [];
    const by: Record<string, TabProps["project"]["members"]> = {};
    project.members.forEach((m) => {
      if (!by[m.skill]) {
        by[m.skill] = [];
        order.push(m.skill);
      }
      by[m.skill].push(m);
    });
    return order.map((skill) => ({ skill, members: by[skill] }));
  }, [project.members]);

  if (memberId) {
    return <MemberView projectId={projectId} project={project} memberId={memberId} onBack={onCloseMember} />;
  }

  return (
    <div className="space-y-6">
      <section className="card space-y-4">
        <h2 className="section-title">Researchers</h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {project.researchers.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => onOpenMember(r.id)}
                className="card-hover flex w-full items-center gap-3 rounded-xl border border-slate-200 p-3 text-left"
              >
                <UserAvatar name={r.name} size="md" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-slate-900">{r.name}</span>
                  <span className="help">{Math.round(r.share_pct * 100) / 100}% share</span>
                </span>
                <span className={r.role === "lead" ? "badge bg-indigo-50 text-indigo-700" : "badge bg-slate-100 text-slate-600"}>
                  {r.role === "lead" ? "Lead" : "Researcher"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className="section-title">Students</h2>
        {groups.length === 0 ? (
          <EmptyState
            icon={<Users className="h-8 w-8" />}
            title="No students yet"
            description="Students appear here once they accept a request."
          />
        ) : (
          groups.map((g) => (
            <div key={g.skill} className="card space-y-3">
              <div className="flex items-center gap-2">
                <SkillChip label={skillLabel(g.skill)} variant="selected" />
                <span className="muted">{g.members.length}</span>
              </div>
              <ul className="grid gap-3 sm:grid-cols-2">
                {g.members.map((m) => (
                  <li key={`${m.student_id}-${m.skill}`}>
                    <button
                      type="button"
                      onClick={() => onOpenMember(m.student_id)}
                      className="card-hover flex w-full items-center gap-3 rounded-xl border border-slate-200 p-3 text-left"
                    >
                      <UserAvatar name={m.name} size="md" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-slate-900">{m.name}</span>
                        <StarRating value={m.rating} size="sm" showValue />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </section>
    </div>
  );
}
