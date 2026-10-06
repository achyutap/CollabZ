"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import { useCounts } from "@/lib/counts";
import type { MatchOut, ProblemOut, ProjectDetail, ResearcherRequestOut } from "@/lib/types";
import { StarRating, StatusBadge, SkillChip, ScoreRing, EmptyState, PageHeader, ConfirmDialog, UserAvatar, Spinner } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import { msg, useErrorToast } from "./util";

const MAX = 5;

export default function MatchesPage({ problemId }: { problemId: string }) {
  const { refresh } = useCounts();
  const problem = useFetch<ProblemOut>(`/problems/${problemId}`);
  const reqs = useFetch<ResearcherRequestOut[]>(`/problems/${problemId}/requests`, { intervalMs: 10000 });
  const [picking, setPicking] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const status = problem.data?.status;
  const canInvite = status === "open" || status === "matched";
  const requests = reqs.data;
  const showPicker = canInvite && requests !== undefined && (requests.length === 0 || picking);
  const matches = useFetch<MatchOut[]>(showPicker ? `/problems/${problemId}/matches` : null);
  const accepted = (requests ?? []).filter((r) => r.status === "accepted" && r.project_id);
  const projectId = accepted.length > 0 ? accepted[0].project_id : null;
  const detail = useFetch<ProjectDetail>(projectId ? `/projects/${projectId}` : null);
  useErrorToast(problem.error);
  useErrorToast(reqs.error);
  useErrorToast(matches.error);

  function roleOf(researcherId: string): "Lead" | "Researcher" {
    const r = detail.data?.researchers.find((x) => x.id === researcherId);
    return r?.role === "lead" ? "Lead" : "Researcher";
  }

  function toggle(id: string) {
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : cur.length >= MAX ? cur : [...cur, id]));
  }

  async function send() {
    setBusy(true);
    try {
      await api.post<ResearcherRequestOut[]>(`/problems/${problemId}/requests`, { researcher_ids: selected });
      toast.success("Requests sent");
      setSelected([]);
      setPicking(false);
      setConfirmOpen(false);
      refresh();
      await Promise.all([reqs.refetch(), problem.refetch()]);
    } catch (e) {
      toast.error(msg(e));
      setConfirmOpen(false);
      await reqs.refetch();
    } finally { setBusy(false); }
  }

  const loading = (problem.loading && !problem.data) || (reqs.loading && !reqs.data);

  return (
    <div className="page pb-28">
      <PageHeader
        title={problem.data ? problem.data.title : "Find researchers"}
        description={problem.data ? `${problem.data.description.slice(0, 160)}${problem.data.description.length > 160 ? "…" : ""}` : undefined}
        actions={problem.data ? <StatusBadge status={problem.data.status} /> : undefined}
      />
      {problem.data && (
        <div className="flex flex-wrap gap-1.5">
          {problem.data.required_skills.map((s) => <SkillChip key={s} label={skillLabel(s)} />)}
        </div>
      )}

      {loading && <div className="flex justify-center py-12"><Spinner /></div>}

      {requests && requests.length > 0 && (
        <section className="space-y-3" aria-label="Requests sent">
          <div className="flex items-center justify-between gap-3">
            <h2 className="section-title">Requests sent</h2>
            {canInvite && !picking && (
              <button className="btn btn-secondary btn-sm" onClick={() => setPicking(true)}>Invite more researchers</button>
            )}
            {picking && <button className="btn btn-ghost btn-sm" onClick={() => { setPicking(false); setSelected([]); }}>Cancel</button>}
          </div>
          {accepted.map((r) => (
            <div key={r.id} className="card flex flex-wrap items-center justify-between gap-3 border-emerald-300 bg-emerald-50 p-4">
              <div className="flex items-center gap-3">
                <UserAvatar name={r.researcher_name} />
                <div>
                  <p className="font-medium">{r.researcher_name} <span className="badge ml-1">{roleOf(r.researcher_id)}</span></p>
                  <p className="muted text-xs">Accepted your request</p>
                </div>
              </div>
              <Link href={`/projects/${r.project_id}`} className="btn btn-primary btn-sm">Open project</Link>
            </div>
          ))}
          <ul className="card divide-y divide-slate-100">
            {requests.filter((r) => r.status !== "accepted").map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-3 p-4">
                <div className="flex items-center gap-3">
                  <UserAvatar name={r.researcher_name} size="sm" />
                  <div>
                    <p className="text-sm font-medium">{r.researcher_name}</p>
                    <p className="muted text-xs">Match {Math.round(r.match_score * 100)}%</p>
                  </div>
                </div>
                <StatusBadge status={r.status} />
              </li>
            ))}
            {requests.filter((r) => r.status !== "accepted").length === 0 && <li className="muted p-4 text-sm">No other requests.</li>}
          </ul>
        </section>
      )}

      {showPicker && (
        <section className="space-y-3" aria-label="Suggested researchers">
          <h2 className="section-title">{requests && requests.length > 0 ? "Invite more researchers" : "Top matches"}</h2>
          {matches.loading && !matches.data ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : !matches.data || matches.data.length === 0 ? (
            <EmptyState
              title="Edit the required skills"
              description="No new researchers match right now. Adjusting the required skills can surface more people."
              action={<Link href="/sponsor/problems" className="btn btn-secondary">Back to problems</Link>}
            />
          ) : (
            <div className="space-y-3">
              {matches.data.map((m) => {
                const checked = selected.includes(m.researcher.id);
                const disabled = !checked && selected.length >= MAX;
                return (
                  <label key={m.researcher.id} className={`card card-hover flex cursor-pointer gap-4 p-4 ${checked ? "border-indigo-400 ring-1 ring-indigo-300" : ""} ${disabled ? "opacity-60" : ""}`}>
                    <input type="checkbox" className="mt-2 h-4 w-4 accent-indigo-600" checked={checked} disabled={disabled} onChange={() => toggle(m.researcher.id)} aria-label={`Select ${m.researcher.name}`} />
                    <UserAvatar name={m.researcher.name} size="lg" />
                    <div className="min-w-0 flex-1 space-y-1.5">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <Link href={`/profile/${m.researcher.id}`} className="font-semibold hover:underline" onClick={(e) => e.stopPropagation()}>{m.researcher.name}</Link>
                        <StarRating value={m.researcher.rating} size="sm" showValue />
                      </div>
                      <p className="muted line-clamp-2 text-sm">{m.researcher.bio}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {m.matched_skills.map((s) => <SkillChip key={s} label={skillLabel(s)} variant="matched" />)}
                        {m.missing_skills.map((s) => <SkillChip key={s} label={skillLabel(s)} variant="missing" />)}
                      </div>
                    </div>
                    <ScoreRing value={m.score} size={56} label="match" />
                  </label>
                );
              })}
            </div>
          )}
        </section>
      )}

      {!canInvite && status === "completed" && requests && (
        <p className="muted text-sm">This problem is completed, so no further researchers can be invited.</p>
      )}

      {selected.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 p-3 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-1 sm:px-3">
            <p className="text-sm font-medium">{selected.length} selected <span className="muted">(max {MAX})</span></p>
            <button className="btn btn-primary" onClick={() => setConfirmOpen(true)}>Send requests</button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Send requests?"
        description={`Invite ${selected.length} researcher${selected.length === 1 ? "" : "s"} to work on this problem. The first to accept becomes the project lead; others join as co-researchers.`}
        confirmLabel="Send requests"
        loading={busy}
        onConfirm={send}
      />
    </div>
  );
}
