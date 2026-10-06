"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Minus, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import { useCounts } from "@/lib/counts";
import type { ProjectDetail, ResearcherShare, ShortlistGroup, SkillNeedOut, StudentOut } from "@/lib/types";
import { StarRating, SkillChip, ScoreRing, EmptyState, PageHeader, ConfirmDialog, UserAvatar, Spinner } from "@/components/common";
import { SKILLS, skillLabel } from "@/components/common/skills";
import { msg, useErrorToast } from "./util";

type NeedRow = { skill: string; count: number };
type Member = ProjectDetail["members"][number];

export default function TeamBuilder({ projectId }: { projectId: string }) {
  const { refresh } = useCounts();
  const detail = useFetch<ProjectDetail>(`/projects/${projectId}`);
  const d = detail.data;
  const canManage = d?.can_manage ?? false;
  const shortlist = useFetch<ShortlistGroup[]>(canManage ? `/projects/${projectId}/shortlist` : null, { intervalMs: 10000 });
  useErrorToast(detail.error);
  useErrorToast(shortlist.error);

  const [rows, setRows] = useState<NeedRow[]>([]);
  const [needsDirty, setNeedsDirty] = useState(false);
  const [savingNeeds, setSavingNeeds] = useState(false);
  const [pendingKeys, setPendingKeys] = useState<string[]>([]);
  const [removeTarget, setRemoveTarget] = useState<Member | null>(null);
  const [removing, setRemoving] = useState(false);
  const [shares, setShares] = useState<Record<string, string>>({});
  const [sharesDirty, setSharesDirty] = useState(false);
  const [savingShares, setSavingShares] = useState(false);

  useEffect(() => {
    if (d && !needsDirty) setRows(d.skill_needs.map((n) => ({ skill: n.skill, count: n.count })));
  }, [d, needsDirty]);
  useEffect(() => {
    if (d && !sharesDirty) {
      const m: Record<string, string> = {};
      d.researchers.forEach((r) => { m[r.id] = String(r.share_pct); });
      setShares(m);
    }
  }, [d, sharesDirty]);

  const filledOf = (skill: string) => d?.skill_needs.find((n) => n.skill === skill)?.filled ?? 0;

  function updateRow(i: number, patch: Partial<NeedRow>) {
    setNeedsDirty(true);
    setRows(rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }
  function addRow() {
    const free = SKILLS.find((s) => !rows.some((r) => r.skill === s.id));
    if (!free) return;
    setNeedsDirty(true);
    setRows([...rows, { skill: free.id, count: 1 }]);
  }
  async function saveNeeds() {
    setSavingNeeds(true);
    try {
      const res = await api.post<SkillNeedOut[]>(`/projects/${projectId}/skill-needs`, rows);
      setRows(res.map((n) => ({ skill: n.skill, count: n.count })));
      setNeedsDirty(false);
      toast.success("Skills needed saved");
      await Promise.all([detail.refetch(), shortlist.refetch()]);
    } catch (e) { toast.error(msg(e)); } finally { setSavingNeeds(false); }
  }

  async function invite(studentId: string, skill: string) {
    const key = `${skill}:${studentId}`;
    setPendingKeys((k) => [...k, key]);
    try {
      await api.post(`/projects/${projectId}/student-requests`, { student_id: studentId, skill });
      toast.success("Request sent");
      refresh();
      await shortlist.refetch();
    } catch (e) {
      setPendingKeys((k) => k.filter((x) => x !== key));
      toast.error(msg(e));
    }
  }

  async function removeStudent() {
    if (!removeTarget) return;
    setRemoving(true);
    try {
      await api.delete<{ status: string }>(`/projects/${projectId}/members/${removeTarget.student_id}`);
      toast.success(`${removeTarget.name} removed`);
      refresh();
      await Promise.all([detail.refetch(), shortlist.refetch()]);
    } catch (e) { toast.error(msg(e)); } finally { setRemoving(false); setRemoveTarget(null); }
  }

  const shareSum = Object.values(shares).reduce((a, v) => a + (Number(v) || 0), 0);
  const shareBad = Object.values(shares).some((v) => v.trim() === "" || !Number.isFinite(Number(v)) || Number(v) < 0);
  const shareError = shareBad ? "Enter a valid percentage for every researcher." : Math.abs(shareSum - 100) > 0.01 ? `Shares must total 100% (currently ${shareSum.toFixed(2)}%).` : "";
  async function saveShares() {
    if (shareError || !d) return;
    setSavingShares(true);
    try {
      await api.put<ResearcherShare[]>(`/projects/${projectId}/researcher-shares`, d.researchers.map((r) => ({ researcher_id: r.id, share_pct: Number(shares[r.id]) })));
      toast.success("Researcher shares saved");
      setSharesDirty(false);
      await detail.refetch();
    } catch (e) { toast.error(msg(e)); } finally { setSavingShares(false); }
  }

  if (detail.loading && !d) return <div className="page flex justify-center py-16"><Spinner /></div>;
  if (!d) return <div className="page"><EmptyState title="Project not found" action={<Link href="/researcher/projects" className="btn btn-secondary">Back to projects</Link>} /></div>;

  const grouped = d.members.reduce<Record<string, Member[]>>((acc, m) => { (acc[m.skill] ||= []).push(m); return acc; }, {});
  const isLead = d.my_role === "lead";

  return (
    <div className="page">
      <PageHeader title="Manage team" description={d.title} actions={<Link href={`/projects/${projectId}`} className="btn btn-secondary">Back to project</Link>} />
      {!canManage && <div className="card p-4 text-sm text-slate-600">This project is not active, so the team can no longer be changed.</div>}

      {canManage && (
        <section className="card space-y-4 p-5" aria-label="Skills needed">
          <h2 className="section-title">1. Skills needed</h2>
          <p className="help">You can change this any time while the project is active. You cannot remove a skill that already has members.</p>
          {rows.length === 0 && <p className="muted text-sm">No skills yet. Add the skills your team needs.</p>}
          <ul className="space-y-2">
            {rows.map((r, i) => {
              const filled = filledOf(r.skill);
              return (
                <li key={i} className="flex flex-wrap items-center gap-2">
                  <label className="sr-only" htmlFor={`need-skill-${i}`}>Skill</label>
                  <select id={`need-skill-${i}`} className="input w-full sm:w-56" value={r.skill} onChange={(e) => updateRow(i, { skill: e.target.value })} disabled={filled > 0}>
                    {SKILLS.filter((s) => s.id === r.skill || !rows.some((x) => x.skill === s.id)).map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                  </select>
                  <div className="flex items-center gap-1" role="group" aria-label={`Count for ${skillLabel(r.skill)}`}>
                    <button type="button" className="btn btn-secondary btn-sm" aria-label="Decrease" disabled={r.count <= Math.max(1, filled)} onClick={() => updateRow(i, { count: r.count - 1 })}><Minus className="h-4 w-4" /></button>
                    <span className="w-8 text-center text-sm font-medium">{r.count}</span>
                    <button type="button" className="btn btn-secondary btn-sm" aria-label="Increase" disabled={r.count >= 10} onClick={() => updateRow(i, { count: r.count + 1 })}><Plus className="h-4 w-4" /></button>
                  </div>
                  <span className="muted text-xs">{filled} filled</span>
                  <button type="button" className="btn btn-ghost btn-sm" aria-label={`Remove ${skillLabel(r.skill)}`} disabled={filled > 0} title={filled > 0 ? "Has members" : "Remove"} onClick={() => { setNeedsDirty(true); setRows(rows.filter((_, idx) => idx !== i)); }}><Trash2 className="h-4 w-4" /></button>
                </li>
              );
            })}
          </ul>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-secondary btn-sm" onClick={addRow} disabled={rows.length >= SKILLS.length}>Add skill</button>
            <button type="button" className="btn btn-primary btn-sm" onClick={saveNeeds} disabled={savingNeeds || !needsDirty || rows.length === 0}>{savingNeeds ? "Saving…" : "Save"}</button>
          </div>
        </section>
      )}

      {canManage && (
        <section className="space-y-3" aria-label="Shortlist">
          <h2 className="section-title">2. Shortlist</h2>
          {shortlist.loading && !shortlist.data ? <Spinner /> : !shortlist.data || shortlist.data.length === 0 ? (
            <EmptyState title="No shortlist yet" description="Save the skills you need to see matching students." />
          ) : shortlist.data.map((g) => {
            const full = g.filled >= g.count;
            const pct = Math.min(100, Math.round((g.filled / Math.max(1, g.count)) * 100));
            return (
              <div key={g.skill} className="card space-y-3 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <SkillChip label={skillLabel(g.skill)} variant="selected" />
                  <span className="muted text-sm">{g.filled}/{g.count} filled{full ? " · Slots full" : ""}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                  <div className="h-full bg-indigo-600" style={{ width: `${pct}%` }} />
                </div>
                {g.candidates.length === 0 ? <p className="muted text-sm">No candidates for this skill yet.</p> : (
                  <ul className="grid gap-3 md:grid-cols-2">
                    {g.candidates.map((c) => {
                      const st = pendingKeys.includes(`${g.skill}:${c.student.id}`) && c.request_status === null ? "pending" : c.request_status;
                      return (
                        <li key={c.student.id} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3">
                          <UserAvatar name={c.student.name} />
                          <div className="min-w-0 flex-1">
                            <Link href={`/profile/${c.student.id}`} className="block truncate text-sm font-medium hover:underline">{c.student.name}</Link>
                            <StarRating value={c.rating} size="sm" showValue />
                            <p className="muted text-xs">{c.projects_done} project{c.projects_done === 1 ? "" : "s"} done</p>
                          </div>
                          <ScoreRing value={c.score} size={44} />
                          {st === null && !full ? (
                            <button className="btn btn-primary btn-sm" onClick={() => invite(c.student.id, g.skill)}>Send request</button>
                          ) : (
                            <button className="btn btn-secondary btn-sm" disabled>
                              {st === "accepted" ? "Joined" : st === "pending" ? "Pending" : st === "declined" ? "Declined" : st === "expired" ? "Expired" : "Slots full"}
                            </button>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </section>
      )}

      {canManage && <StudentSearch projectId={projectId} needs={d.skill_needs} onInvited={() => { refresh(); void shortlist.refetch(); }} />}

      <section className="card space-y-4 p-5" aria-label="Current team">
        <h2 className="section-title">{canManage ? "4. Current team" : "Team"}</h2>
        {d.members.length === 0 ? <p className="muted text-sm">No students have joined yet.</p> : Object.entries(grouped).map(([skill, ms]) => (
          <div key={skill} className="space-y-2">
            <SkillChip label={skillLabel(skill)} />
            <ul className="divide-y divide-slate-100">
              {ms.map((m) => (
                <li key={m.student_id} className="flex items-center gap-3 py-2">
                  <UserAvatar name={m.name} size="sm" />
                  <Link href={`/profile/${m.student_id}`} className="flex-1 truncate text-sm font-medium hover:underline">{m.name}</Link>
                  <StarRating value={m.rating} size="sm" />
                  {canManage && <button className="btn btn-danger btn-sm" onClick={() => setRemoveTarget(m)}>Remove</button>}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section className="card space-y-3 p-5" aria-label="Researchers">
        <h2 className="section-title">{canManage ? "5. Researchers" : "Researchers"}</h2>
        <ul className="space-y-2">
          {d.researchers.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center gap-3">
              <UserAvatar name={r.name} size="sm" />
              <Link href={`/profile/${r.id}`} className="flex-1 text-sm font-medium hover:underline">{r.name}</Link>
              <span className="badge">{r.role === "lead" ? "Lead" : "Researcher"}</span>
              {isLead && canManage ? (
                <div className="flex items-center gap-1">
                  <label className="sr-only" htmlFor={`share-${r.id}`}>Share % for {r.name}</label>
                  <input id={`share-${r.id}`} type="number" min={0} max={100} step="0.01" className="input w-24 text-right" value={shares[r.id] ?? ""} onChange={(e) => { setSharesDirty(true); setShares({ ...shares, [r.id]: e.target.value }); }} />
                  <span className="text-sm">%</span>
                </div>
              ) : <span className="text-sm font-medium">{r.share_pct}%</span>}
            </li>
          ))}
        </ul>
        {isLead && canManage ? (
          <div className="space-y-2">
            {shareError && sharesDirty && <p className="error-text">{shareError}</p>}
            <button className="btn btn-primary btn-sm" disabled={savingShares || !sharesDirty || Boolean(shareError)} onClick={saveShares}>{savingShares ? "Saving…" : "Save shares"}</button>
          </div>
        ) : <p className="help">Only the lead researcher can edit shares.</p>}
      </section>

      <ConfirmDialog
        open={removeTarget !== null}
        onOpenChange={(o) => { if (!o) setRemoveTarget(null); }}
        title={`Remove ${removeTarget?.name ?? "student"}?`}
        description="They keep credit for approved work."
        confirmLabel="Remove"
        destructive
        loading={removing}
        onConfirm={removeStudent}
      />
    </div>
  );
}

function StudentSearch({ projectId, needs, onInvited }: { projectId: string; needs: SkillNeedOut[]; onInvited: () => void }) {
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [skill, setSkill] = useState("");
  const [results, setResults] = useState<StudentOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [sent, setSent] = useState<string[]>([]);

  useEffect(() => { const t = setTimeout(() => setDq(q.trim()), 350); return () => clearTimeout(t); }, [q]);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.get<StudentOut[]>(`/projects/${projectId}/student-search`, { q: dq || undefined, skill: skill || undefined })
      .then((r) => { if (alive) setResults(r); })
      .catch((e: unknown) => { if (alive) toast.error(msg(e)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [projectId, dq, skill]);

  async function invite(s: StudentOut) {
    const sk = choice[s.id] ?? needs[0]?.skill;
    if (!sk) { toast.error("Add a skill need first."); return; }
    try {
      await api.post(`/projects/${projectId}/student-requests`, { student_id: s.id, skill: sk });
      setSent((x) => [...x, s.id]);
      toast.success(`Request sent to ${s.name}`);
      onInvited();
    } catch (e) { toast.error(msg(e)); }
  }

  return (
    <section className="card space-y-3 p-5" aria-label="Add any student">
      <h2 className="section-title">3. Add any student</h2>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="flex-1">
          <label className="sr-only" htmlFor="stu-q">Search students</label>
          <input id="stu-q" className="input" placeholder="Search by name…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div>
          <label className="sr-only" htmlFor="stu-skill">Filter by skill</label>
          <select id="stu-skill" className="input" value={skill} onChange={(e) => setSkill(e.target.value)}>
            <option value="">All skills</option>
            {SKILLS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </div>
      </div>
      {needs.length === 0 && <p className="help">Save at least one skill need above to invite students.</p>}
      {loading ? <Spinner /> : results.length === 0 ? <p className="muted text-sm">No students found.</p> : (
        <ul className="divide-y divide-slate-100">
          {results.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center gap-3 py-2">
              <UserAvatar name={s.name} size="sm" />
              <div className="min-w-0 flex-1">
                <Link href={`/profile/${s.id}`} className="block truncate text-sm font-medium hover:underline">{s.name}</Link>
                <div className="flex flex-wrap items-center gap-1">
                  <StarRating value={s.rating} size="sm" />
                  {s.skills.slice(0, 3).map((k) => <SkillChip key={k} label={skillLabel(k)} />)}
                </div>
              </div>
              <label className="sr-only" htmlFor={`inv-${s.id}`}>Skill for {s.name}</label>
              <select id={`inv-${s.id}`} className="input w-40" value={choice[s.id] ?? needs[0]?.skill ?? ""} onChange={(e) => setChoice({ ...choice, [s.id]: e.target.value })}>
                {needs.map((n) => <option key={n.skill} value={n.skill}>{skillLabel(n.skill)}</option>)}
              </select>
              <button className="btn btn-primary btn-sm" disabled={needs.length === 0 || sent.includes(s.id)} onClick={() => invite(s)}>{sent.includes(s.id) ? "Invited" : "Invite"}</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
