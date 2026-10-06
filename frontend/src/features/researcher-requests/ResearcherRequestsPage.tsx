"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import { useCounts } from "@/lib/counts";
import type { ResearcherRequestOut } from "@/lib/types";
import { StatusBadge, SkillChip, ScoreRing, MoneyText, EmptyState, PageHeader, ConfirmDialog, Tabs, Spinner } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import { formatDate } from "@/components/common/format";
import { inr, msg, useErrorToast } from "./util";

type Target = { req: ResearcherRequestOut; accept: boolean };

export default function ResearcherRequestsPage() {
  const router = useRouter();
  const { refresh } = useCounts();
  const { data, error, loading, refetch } = useFetch<ResearcherRequestOut[]>("/researcher/requests", { intervalMs: 15000 });
  useErrorToast(error);
  const [tab, setTab] = useState("pending");
  const [open, setOpen] = useState<string[]>([]);
  const [target, setTarget] = useState<Target | null>(null);
  const [busy, setBusy] = useState(false);

  const all = data ?? [];
  const pending = all.filter((r) => r.status === "pending");
  const accepted = all.filter((r) => r.status === "accepted");
  const other = all.filter((r) => r.status === "declined" || r.status === "expired");
  const list = tab === "pending" ? pending : tab === "accepted" ? accepted : other;

  async function respond() {
    if (!target) return;
    setBusy(true);
    try {
      const res = await api.post<{ status: string; project_id: string | null }>(`/researcher-requests/${target.req.id}/respond`, { accept: target.accept });
      refresh();
      if (target.accept && res.project_id) {
        toast.success("You joined the project");
        router.push(`/projects/${res.project_id}`);
        return;
      }
      toast.success(target.accept ? "Request accepted" : "Request declined");
      await refetch();
    } catch (e) {
      toast.error(msg(e));
      await refetch();
    } finally { setBusy(false); setTarget(null); }
  }

  return (
    <div className="page">
      <PageHeader title="Requests" description="Sponsors who want you on their problem." />
      <Tabs
        tabs={[{ id: "pending", label: "Pending", count: pending.length }, { id: "accepted", label: "Accepted" }, { id: "other", label: "Other" }]}
        active={tab}
        onChange={setTab}
      />
      {loading && !data ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : list.length === 0 ? (
        <EmptyState title={tab === "pending" ? "No pending requests" : tab === "accepted" ? "No accepted requests yet" : "Nothing here"} description="New sponsor requests appear here automatically." />
      ) : (
        <div className="space-y-4">
          {list.map((r) => {
            const expanded = open.includes(r.id);
            const p = r.problem;
            return (
              <article key={r.id} className="card space-y-3 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="font-semibold text-slate-900">{p.title}</h2>
                    <p className="muted text-xs">From {r.sponsor_name} · {formatDate(r.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <ScoreRing value={r.match_score} size={48} label="match" />
                    <StatusBadge status={r.status} />
                  </div>
                </div>
                <p className={`text-sm text-slate-700 ${expanded ? "" : "line-clamp-2"}`}>{p.description}</p>
                <button className="text-xs font-medium text-indigo-600 hover:underline" aria-expanded={expanded} onClick={() => setOpen(expanded ? open.filter((x) => x !== r.id) : [...open, r.id])}>
                  {expanded ? "Show less" : "Show more"}
                </button>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                  <MoneyText amount={p.budget} className="font-semibold" />
                  <span className="muted">{p.student_pct}% students ({inr((p.budget * p.student_pct) / 100)})</span>
                  <span className="muted">{p.researcher_pct}% researchers</span>
                </div>
                <div className="flex flex-wrap gap-1.5">{p.required_skills.map((s) => <SkillChip key={s} label={skillLabel(s)} />)}</div>
                {r.status === "pending" && (
                  <div className="flex gap-2 pt-1">
                    <button className="btn btn-primary" onClick={() => setTarget({ req: r, accept: true })}>Accept</button>
                    <button className="btn btn-secondary" onClick={() => setTarget({ req: r, accept: false })}>Decline</button>
                  </div>
                )}
                {r.status === "accepted" && r.project_id && (
                  <Link href={`/projects/${r.project_id}`} className="btn btn-secondary btn-sm">Open project</Link>
                )}
              </article>
            );
          })}
        </div>
      )}
      <ConfirmDialog
        open={target !== null}
        onOpenChange={(o) => { if (!o) setTarget(null); }}
        title={target?.accept ? "Accept this request?" : "Decline this request?"}
        description={target?.accept ? "You will join this project. If you are the first researcher you become the lead; otherwise you join as a co-researcher." : "The sponsor will see that you declined."}
        confirmLabel={target?.accept ? "Accept" : "Decline"}
        destructive={target ? !target.accept : false}
        loading={busy}
        onConfirm={respond}
      />
    </div>
  );
}
