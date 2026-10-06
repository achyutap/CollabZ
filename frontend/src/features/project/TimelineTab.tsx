"use client";

import { useMemo, useState } from "react";
import { useFetch } from "@/lib/hooks";
import type { ActivityItem } from "@/lib/types";
import { Spinner, Timeline } from "@/components/common";
import type { TabProps } from "./components/tabTypes";
import { useErrorToast } from "./components/hooks";

export default function TimelineTab({ projectId, project }: TabProps) {
  const [person, setPerson] = useState("");
  const { data, error, loading } = useFetch<ActivityItem[]>(`/projects/${projectId}/activity`, {
    params: { user_id: person || undefined, limit: "100" },
    intervalMs: 15000,
  });
  useErrorToast(error);

  const options = useMemo(() => {
    const m = new Map<string, string>();
    project.researchers.forEach((r) => m.set(r.id, r.name));
    project.members.forEach((s) => m.set(s.student_id, s.name));
    (data ?? []).forEach((a) => {
      if (a.actor) m.set(a.actor.id, a.actor.name);
    });
    if (person && !m.has(person)) m.set(person, "Selected person");
    return Array.from(m.entries());
  }, [project.researchers, project.members, data, person]);

  return (
    <section className="card space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="section-title">Timeline</h2>
        <div>
          <label htmlFor="tl-person" className="label">Person</label>
          <select id="tl-person" value={person} onChange={(e) => setPerson(e.target.value)} className="input">
            <option value="">Everyone</option>
            {options.map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
        </div>
      </div>
      {loading && !data ? (
        <div className="flex justify-center py-6"><Spinner /></div>
      ) : (
        <Timeline items={data ?? []} onActorClick={(id) => setPerson(id)} emptyText="No activity yet." />
      )}
    </section>
  );
}
