"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Heart, Search } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import type { PersonCard, PublicProjectCard } from "@/lib/types";
import { StarRating, StatusBadge, SkillChip, EmptyState, PageHeader, Tabs, UserAvatar, Spinner } from "@/components/common";
import { SKILLS, skillLabel } from "@/components/common/skills";
import { useErrorToast } from "./util";

const ROLES = ["", "student", "researcher", "sponsor"];

export default function ExplorePage() {
  const [tab, setTab] = useState("projects");
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [skill, setSkill] = useState("");
  const [role, setRole] = useState("");
  useEffect(() => { const t = setTimeout(() => setDq(q.trim()), 300); return () => clearTimeout(t); }, [q]);
  const pParams = useMemo(() => ({ q: dq || undefined, skill: skill || undefined }), [dq, skill]);
  const uParams = useMemo(() => ({ q: dq || undefined, role: role || undefined }), [dq, role]);
  const projects = useFetch<PublicProjectCard[]>(tab === "projects" ? "/explore/projects" : null, { params: pParams });
  const people = useFetch<PersonCard[]>(tab === "people" ? "/explore/people" : null, { params: uParams });
  useErrorToast(projects.error);
  useErrorToast(people.error);

  return (
    <div className="page">
      <PageHeader title="Explore" description="Discover public projects and people on CollabZ." />
      <Tabs tabs={[{ id: "projects", label: "Projects" }, { id: "people", label: "People" }]} active={tab} onChange={setTab} />
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
        <label className="sr-only" htmlFor="explore-q">Search</label>
        <input id="explore-q" className="input pl-9" placeholder={tab === "projects" ? "Search projects…" : "Search people…"} value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {tab === "projects" ? (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by skill">
          <SkillChip label="All" variant={skill === "" ? "selected" : "default"} onClick={() => setSkill("")} />
          {SKILLS.map((s) => <SkillChip key={s.id} label={s.label} variant={skill === s.id ? "selected" : "default"} onClick={() => setSkill(skill === s.id ? "" : s.id)} />)}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by role">
          {ROLES.map((r) => <SkillChip key={r || "all"} label={r ? r[0].toUpperCase() + r.slice(1) : "Everyone"} variant={role === r ? "selected" : "default"} onClick={() => setRole(r)} />)}
        </div>
      )}

      {tab === "projects" ? (
        projects.loading && !projects.data ? <div className="flex justify-center py-12"><Spinner /></div> :
        !projects.data || projects.data.length === 0 ? <EmptyState title="No public projects found" description="Projects appear here once researchers publish files." /> : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.data.map((p) => (
              <Link key={p.project_id} href={`/explore/${p.project_id}`} className="card card-hover block space-y-3 p-5">
                <div className="flex items-start justify-between gap-2"><h2 className="font-semibold text-slate-900">{p.title}</h2><StatusBadge status={p.status} /></div>
                <p className="muted line-clamp-3 text-sm">{p.summary}</p>
                <div className="flex flex-wrap gap-1.5">{p.required_skills.map((s) => <SkillChip key={s} label={skillLabel(s)} />)}</div>
                <div className="flex items-center justify-between">
                  <div className="flex -space-x-2">{[...p.researchers, ...p.members].slice(0, 5).map((u) => <span key={u.id} className="rounded-full ring-2 ring-white"><UserAvatar name={u.name} size="sm" /></span>)}</div>
                  <span className="muted text-xs">{p.public_file_count} public file{p.public_file_count === 1 ? "" : "s"}</span>
                </div>
              </Link>
            ))}
          </div>
        )
      ) : (
        people.loading && !people.data ? <div className="flex justify-center py-12"><Spinner /></div> :
        !people.data || people.data.length === 0 ? <EmptyState title="No people found" description="Try a different search." /> : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {people.data.map((u) => (
              <Link key={u.id} href={`/profile/${u.id}`} className="card card-hover block space-y-3 p-5">
                <div className="flex items-center gap-3">
                  <UserAvatar name={u.name} />
                  <div className="min-w-0"><p className="truncate font-semibold text-slate-900">{u.name}</p><p className="muted text-xs capitalize">{u.role}</p></div>
                </div>
                {u.headline && <p className="muted line-clamp-2 text-sm">{u.headline}</p>}
                <div className="flex flex-wrap gap-1.5">{u.skills.slice(0, 4).map((s) => <SkillChip key={s} label={skillLabel(s)} />)}</div>
                <div className="flex items-center justify-between">
                  {u.role !== "sponsor" ? <StarRating value={u.rating} size="sm" /> : <span />}
                  <span className="muted inline-flex items-center gap-1 text-xs"><Heart className="h-3.5 w-3.5" aria-hidden />{u.likes_count}</span>
                </div>
              </Link>
            ))}
          </div>
        )
      )}
    </div>
  );
}
