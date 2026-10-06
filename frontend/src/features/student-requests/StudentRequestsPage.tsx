"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import { useCounts } from "@/lib/counts";
import type { StudentRequestOut } from "@/lib/types";
import { StatusBadge, SkillChip, EmptyState, PageHeader, ConfirmDialog, Tabs, Spinner } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import { formatDate } from "@/components/common/format";
import { msg, useErrorToast } from "./util";

type Target = { req: StudentRequestOut; accept: boolean };

export default function StudentRequestsPage() {
  const router = useRouter();
  const { refresh } = useCounts();
  const { data, error, loading, refetch } = useFetch<StudentRequestOut[]>("/student/requests", { intervalMs: 15000 });
  useErrorToast(error);
  const [tab, setTab] = useState("pending");
  const [target, setTarget] = useState<Target | null>(null);
  const [busy, setBusy] = useState(false);

  const all = data ?? [];
  const pending = all.filter((r) => r.status === "pending");
  const history = all.filter((r) => r.status !== "pending");
  const list = tab === "pending" ? pending : history;

  async function respond() {
    if (!target) return;
    setBusy(true);
    try {
      await api.post<{ status: string }>(`/student-requests/${target.req.id}/respond`, { accept: target.accept });
      refresh();
      if (target.accept) {
        toast.success("You joined the project");
        router.push(`/projects/${target.req.project_id}`);
        return;
      }
      toast.success("Request declined");
      await refetch();
    } catch (e) {
      toast.error(e instanceof ApiError && e.status === 409 ? "Slots for this skill are full" : msg(e));
      await refetch();
    } finally { setBusy(false); setTarget(null); }
  }

  return (
    <div className="page">
      <PageHeader title="Requests" description="Researchers who want you on their project." />
      <Tabs
        tabs={[{ id: "pending", label: "Pending", count: pending.length }, { id: "history", label: "History" }]}
        active={tab}
        onChange={setTab}
      />
      {loading && !data ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : list.length === 0 ? (
        <EmptyState title={tab === "pending" ? "No pending requests" : "No history yet"} description="Requests from researchers will show up here." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {list.map((r) => (
            <article key={r.id} className="card space-y-3 p-5">
              <div className="flex items-start justify-between gap-3">
                <h2 className="font-semibold text-slate-900">{r.project_title}</h2>
                <StatusBadge status={r.status} />
              </div>
              <p className="muted text-sm">From {r.researcher_name} · {formatDate(r.created_at)}</p>
              <SkillChip label={skillLabel(r.skill)} variant="selected" />
              {r.status === "pending" && (
                <div className="flex gap-2">
                  <button className="btn btn-primary" onClick={() => setTarget({ req: r, accept: true })}>Accept</button>
                  <button className="btn btn-secondary" onClick={() => setTarget({ req: r, accept: false })}>Decline</button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      <ConfirmDialog
        open={target !== null}
        onOpenChange={(o) => { if (!o) setTarget(null); }}
        title={target?.accept ? "Join this project?" : "Decline this request?"}
        description={target?.accept ? `You will work on "${target.req.project_title}" as ${skillLabel(target.req.skill)}.` : "The researcher will see that you declined."}
        confirmLabel={target?.accept ? "Join" : "Decline"}
        destructive={target ? !target.accept : false}
        loading={busy}
        onConfirm={respond}
      />
    </div>
  );
}
