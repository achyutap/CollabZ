"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Inbox } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import { ConfirmDialog, EmptyState, MoneyText, PageHeader, ScoreRing, SkillChip, Spinner, StatusBadge } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import type { ResearcherRequestOut } from "@/lib/types";

type Tab = "pending" | "accepted" | "other";
type Pending = { req: ResearcherRequestOut; accept: boolean } | null;

const TABS: { id: Tab; label: string }[] = [
  { id: "pending", label: "Pending" },
  { id: "accepted", label: "Accepted" },
  { id: "other", label: "Other" },
];

function RequestCard({
  req,
  onAction,
}: {
  req: ResearcherRequestOut;
  onAction: (req: ResearcherRequestOut, accept: boolean) => void;
}) {
  const [open, setOpen] = useState(false);
  const p = req.problem;
  const pool = (p.budget * p.student_pct) / 100;
  const long = p.description.length > 180;
  const text = open || !long ? p.description : `${p.description.slice(0, 180)}…`;
  return (
    <li className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-slate-900">{p.title}</h3>
          <p className="text-xs text-slate-500">Sponsor: {req.sponsor_name}</p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <ScoreRing value={req.match_score} size={44} />
          <StatusBadge status={req.status} />
        </div>
      </div>
      <div>
        <p className="whitespace-pre-line text-sm text-slate-700">{text}</p>
        {long && (
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="mt-1 text-xs font-medium text-indigo-600 hover:underline">
            {open ? "Show less" : "Show more"}
          </button>
        )}
      </div>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm text-slate-600">
        <MoneyText amount={p.budget} className="font-semibold text-slate-900" />
        <span>{p.student_pct}% to students (<MoneyText amount={pool} />)</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {p.required_skills.map((s) => (
          <SkillChip key={s} label={skillLabel(s)} />
        ))}
      </div>
      {req.status === "pending" && (
        <div className="flex flex-wrap gap-2 pt-1">
          <button type="button" onClick={() => onAction(req, true)} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            Accept
          </button>
          <button type="button" onClick={() => onAction(req, false)} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
            Decline
          </button>
        </div>
      )}
      {req.status === "accepted" && req.project_id && (
        <Link href={`/projects/${req.project_id}`} className="inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700">
          Open project
        </Link>
      )}
    </li>
  );
}

export default function ResearcherRequests() {
  const router = useRouter();
  const { data, error, loading, refetch } = useFetch<ResearcherRequestOut[]>("/researcher/requests", { intervalMs: 15000 });
  const [tab, setTab] = useState<Tab>("pending");
  const [pending, setPending] = useState<Pending>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (error) toast.error(error.detail);
  }, [error]);

  const groups = useMemo(() => {
    const list = data ?? [];
    return {
      pending: list.filter((r) => r.status === "pending"),
      accepted: list.filter((r) => r.status === "accepted"),
      other: list.filter((r) => r.status === "declined" || r.status === "expired"),
    };
  }, [data]);

  async function respond() {
    if (!pending) return;
    const { req, accept } = pending;
    setBusy(true);
    try {
      const res = await api.post<{ status: string; project_id: string | null }>(`/researcher-requests/${req.id}/respond`, { accept });
      setPending(null);
      if (accept && res.project_id) {
        toast.success("You are now leading this project");
        router.push(`/researcher/projects/${res.project_id}/team`);
        return;
      }
      toast.success(accept ? "Request accepted" : "Request declined");
      await refetch();
    } catch (err) {
      setPending(null);
      if (err instanceof ApiError && err.status === 409) {
        toast.error("Already taken by another researcher");
      } else {
        toast.error(err instanceof ApiError ? err.detail : "Could not respond");
      }
      await refetch();
    } finally {
      setBusy(false);
    }
  }

  const current = groups[tab];

  return (
    <div className="space-y-6">
      <PageHeader title="Requests" description="Problems sponsors have invited you to lead." />
      <div role="tablist" aria-label="Request status" className="flex gap-1 rounded-lg bg-slate-100 p-1 sm:w-fit">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            type="button"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 rounded-md px-4 py-1.5 text-sm font-medium sm:flex-none ${tab === t.id ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
          >
            {t.label} ({groups[t.id].length})
          </button>
        ))}
      </div>

      {loading && !data ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : current.length === 0 ? (
        <EmptyState
          title={tab === "pending" ? "No pending requests" : tab === "accepted" ? "No accepted requests yet" : "Nothing here"}
          description={tab === "pending" ? "New invitations from sponsors will appear here." : undefined}
          icon={<Inbox className="h-8 w-8" aria-hidden="true" />}
        />
      ) : (
        <ul className="space-y-4">
          {current.map((r) => (
            <RequestCard key={r.id} req={r} onAction={(req, accept) => setPending({ req, accept })} />
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(o) => { if (!o) setPending(null); }}
        title={pending?.accept ? "Accept this request?" : "Decline this request?"}
        description={
          pending?.accept
            ? "You will lead this project. Other researchers' requests will close."
            : "The sponsor will see that you declined."
        }
        confirmLabel={pending?.accept ? "Accept" : "Decline"}
        destructive={pending ? !pending.accept : false}
        loading={busy}
        onConfirm={respond}
      />
    </div>
  );
}
