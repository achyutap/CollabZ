"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Inbox } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import { ConfirmDialog, EmptyState, PageHeader, SkillChip, Spinner, StatusBadge } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import type { StudentRequestOut } from "@/lib/types";

type Tab = "pending" | "history";
type Pending = { req: StudentRequestOut; accept: boolean } | null;

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export default function StudentRequests() {
  const router = useRouter();
  const { data, error, loading, refetch } = useFetch<StudentRequestOut[]>("/student/requests", { intervalMs: 15000 });
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
      history: list.filter((r) => r.status !== "pending"),
    };
  }, [data]);

  async function respond() {
    if (!pending) return;
    const { req, accept } = pending;
    setBusy(true);
    try {
      await api.post<{ status: string }>(`/student-requests/${req.id}/respond`, { accept });
      setPending(null);
      if (accept) {
        toast.success("You joined the project");
        router.push(`/projects/${req.project_id}`);
        return;
      }
      toast.success("Request declined");
      await refetch();
    } catch (err) {
      setPending(null);
      if (err instanceof ApiError && err.status === 409) {
        toast.error("Slots for this skill are full");
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
      <PageHeader title="Project requests" description="Researchers who want you on their team." />
      <div role="tablist" aria-label="Request status" className="flex gap-1 rounded-lg bg-slate-100 p-1 sm:w-fit">
        {(["pending", "history"] as Tab[]).map((t) => (
          <button
            key={t}
            role="tab"
            type="button"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-md px-4 py-1.5 text-sm font-medium sm:flex-none ${tab === t ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
          >
            {t === "pending" ? "Pending" : "History"} ({groups[t].length})
          </button>
        ))}
      </div>

      {loading && !data ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : current.length === 0 ? (
        <EmptyState
          title={tab === "pending" ? "No pending requests" : "No history yet"}
          description={tab === "pending" ? "When a researcher invites you, it shows up here." : undefined}
          icon={<Inbox className="h-8 w-8" aria-hidden="true" />}
        />
      ) : (
        <ul className="space-y-4">
          {current.map((r) => (
            <li key={r.id} className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-slate-900">{r.project_title}</h3>
                  <p className="text-xs text-slate-500">From {r.researcher_name} · {formatDate(r.created_at)}</p>
                </div>
                <StatusBadge status={r.status} />
              </div>
              <SkillChip label={skillLabel(r.skill)} />
              {r.status === "pending" && (
                <div className="flex flex-wrap gap-2 pt-1">
                  <button type="button" onClick={() => setPending({ req: r, accept: true })} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                    Accept
                  </button>
                  <button type="button" onClick={() => setPending({ req: r, accept: false })} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                    Decline
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(o) => { if (!o) setPending(null); }}
        title={pending?.accept ? "Join this project?" : "Decline this request?"}
        description={
          pending
            ? pending.accept
              ? `You will join "${pending.req.project_title}" as ${skillLabel(pending.req.skill)}.`
              : `You will not join "${pending.req.project_title}".`
            : ""
        }
        confirmLabel={pending?.accept ? "Accept" : "Decline"}
        destructive={pending ? !pending.accept : false}
        loading={busy}
        onConfirm={respond}
      />
    </div>
  );
}
