"use client";

import { useState } from "react";
import { Download, Hourglass, Info, Printer } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { PayoutOut, ProjectDetail, SubmissionOut } from "@/lib/types";
import { ConfirmDialog, DonutChart, EmptyState, MoneyText, Spinner, StarRating } from "@/components/common";
import { formatDate } from "@/components/common/format";
import type { TabProps } from "./components/tabTypes";
import FadeIn from "./components/FadeIn";
import { useErrorToast } from "./components/hooks";
import { errMsg, pctLabel } from "./components/format";
import { inr } from "./components/money";

const C_STUDENTS = "#4f46e5";
const C_RESEARCHERS = "#10b981";
const C_FUND = "#f59e0b";

function donutData(studentPool: number, researcherPool: number, projectFund: number) {
  return [
    { label: "Students", value: studentPool, color: C_STUDENTS },
    { label: "Researchers", value: researcherPool, color: C_RESEARCHERS },
    { label: "Project fund", value: projectFund, color: C_FUND },
  ];
}

function Stat({ label, amount }: { label: string; amount: number }) {
  return (
    <div className="card">
      <p className="help">{label}</p>
      <MoneyText amount={amount} className="mt-1 block text-lg font-semibold text-slate-900" />
    </div>
  );
}

export default function BudgetTab({ projectId, project, onChanged, refreshCounts }: TabProps) {
  const [result, setResult] = useState<PayoutOut | null>(null);

  if (project.status === "completed" || result) {
    return <PayoutView projectId={projectId} initial={result} />;
  }
  return (
    <PlannedBudget
      projectId={projectId}
      project={project}
      onCompleted={async (res) => {
        setResult(res);
        await Promise.all([onChanged(), refreshCounts()]);
      }}
    />
  );
}

/* ---------------------------- Before completion ---------------------------- */

function PlannedBudget({
  projectId,
  project,
  onCompleted,
}: {
  projectId: string;
  project: ProjectDetail;
  onCompleted: (r: PayoutOut) => Promise<void>;
}) {
  const b = project.budget;
  return (
    <div className="space-y-6">
      <section className="card">
        <h2 className="section-title">Budget split</h2>
        <div className="mt-4">
          <DonutChart
            data={donutData(b.student_pool, b.researcher_pool, b.project_fund)}
            centerLabel="Total budget"
            centerValue={inr(b.total)}
            size={200}
            formatValue={inr}
          />
        </div>
      </section>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Total budget" amount={b.total} />
        <Stat label="Student pool" amount={b.student_pool} />
        <Stat label="Researcher pool" amount={b.researcher_pool} />
        <Stat label="Project fund" amount={b.project_fund} />
      </div>

      <section className="card space-y-3">
        <h2 className="section-title">Researchers</h2>
        <div className="overflow-x-auto">
          <table className="table-clean w-full min-w-[420px] text-left text-sm">
            <thead>
              <tr>
                <th>Researcher</th>
                <th>Share</th>
                <th>Estimated amount</th>
              </tr>
            </thead>
            <tbody>
              {project.researchers.map((r) => (
                <tr key={r.id}>
                  <td>
                    {r.name}
                    {r.role === "lead" && <span className="badge ml-2 bg-indigo-50 text-indigo-700">Lead</span>}
                  </td>
                  <td className="tabular-nums">{Math.round(r.share_pct * 100) / 100}%</td>
                  <td><MoneyText amount={(b.researcher_pool * r.share_pct) / 100} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="help">Student amounts are calculated from approved, original work when the project is completed.</p>
      </section>

      {project.my_role === "lead" && <CompleteCard projectId={projectId} onDone={onCompleted} />}
      {project.my_role === "researcher" && (
        <div className="card flex items-start gap-2 text-sm text-slate-600">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" aria-hidden="true" />
          Only the lead researcher can complete the project.
        </div>
      )}
    </div>
  );
}

function CompleteCard({ projectId, onDone }: { projectId: string; onDone: (r: PayoutOut) => Promise<void> }) {
  const pending = useFetch<SubmissionOut[]>(`/projects/${projectId}/submissions`, { params: { status: "pending" } });
  useErrorToast(pending.error);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const count = pending.data ? pending.data.filter((s) => s.status === "pending").length : null;
  const blocked = count === null || count > 0;

  async function complete() {
    setBusy(true);
    try {
      const res = await api.post<PayoutOut>(`/projects/${projectId}/complete`);
      setOpen(false);
      toast.success("Project completed and funds paid out");
      await onDone(res);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card space-y-3">
      <h2 className="section-title">Complete project</h2>
      <p className="muted">
        Completing pays out the budget. Student rewards come from approved, original work and its quality; the
        project fund goes to you as operating funds. Review every pending submission first.
      </p>
      {pending.loading && !pending.data ? (
        <Spinner />
      ) : (
        <>
          {count !== null && count > 0 && (
            <p role="status" className="text-sm text-amber-700">
              {count} {count === 1 ? "submission" : "submissions"} still pending, review them first
            </p>
          )}
          <button type="button" disabled={blocked} onClick={() => setOpen(true)} className="btn btn-primary">
            Complete project
          </button>
        </>
      )}
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Complete this project?"
        description="This cannot be undone. Funds will be paid out."
        confirmLabel="Complete project"
        destructive
        loading={busy}
        onConfirm={complete}
      />
    </section>
  );
}

/* ----------------------------- After completion ----------------------------- */

const KIND_LABEL: Record<PayoutOut["transactions"][number]["kind"], string> = {
  student_reward: "Student reward",
  researcher_share: "Researcher share",
  project_fund: "Project fund",
  refund: "Refund",
};

function csvCell(v: string | number): string {
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function exportCsv(p: PayoutOut): void {
  const rows: (string | number)[][] = [
    ["Researchers"],
    ["Name", "Role", "Share %", "Amount"],
    ...p.researchers.map((r) => [r.name, r.role, r.share_pct, r.amount.toFixed(2)]),
    [],
    ["Students"],
    ["Name", "Status", "Submitted", "Approved", "Files", "Approval ratio %", "Quality %", "Share %", "Amount", "Project score", "Old rating", "New rating"],
    ...p.students.map((s) => [
      s.name,
      s.status,
      s.submitted,
      s.approved,
      s.files_count,
      pctLabel(s.approval_ratio).replace("%", ""),
      pctLabel(s.impact).replace("%", ""),
      s.share_pct,
      s.amount.toFixed(2),
      s.project_score,
      s.old_rating ?? "",
      s.new_final_rating,
    ]),
    [],
    ["Transactions"],
    ["Name", "Role", "Kind", "Amount"],
    ...p.transactions.map((t) => [t.name, t.role, KIND_LABEL[t.kind], t.amount.toFixed(2)]),
    ["Total", "", "", p.transactions.reduce((a, t) => a + t.amount, 0).toFixed(2)],
  ];
  const csv = rows.map((r) => r.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `payout-${p.project_id}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function PayoutView({ projectId, initial }: { projectId: string; initial: PayoutOut | null }) {
  const { user } = useAuth();
  const { data: fetched, error, loading } = useFetch<PayoutOut>(initial ? null : `/projects/${projectId}/payout`);
  useErrorToast(error);
  const p = initial ?? fetched;

  if (!p) {
    return loading ? (
      <div className="flex justify-center py-10"><Spinner /></div>
    ) : (
      <EmptyState icon={<Hourglass className="h-8 w-8" />} title="Payout unavailable" description={error?.detail ?? "Could not load the payout."} />
    );
  }

  const mine = p.students.find((s) => s.student_id === user?.id);
  const ledgerTotal = p.transactions.reduce((a, t) => a + t.amount, 0);

  return (
    <div className="space-y-6">
      <style>{`@media print{nav,aside,[role="tablist"],.no-print{display:none !important}.card{box-shadow:none !important;border:1px solid #ddd !important;break-inside:avoid}}`}</style>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="section-title">Payout</h2>
          {p.completed_at && <p className="muted">Completed {formatDate(p.completed_at)}</p>}
        </div>
        <div className="no-print flex gap-2">
          <button type="button" onClick={() => exportCsv(p)} className="btn btn-secondary btn-sm">
            <Download className="h-4 w-4" aria-hidden="true" /> Download CSV
          </button>
          <button type="button" onClick={() => window.print()} className="btn btn-secondary btn-sm">
            <Printer className="h-4 w-4" aria-hidden="true" /> Print
          </button>
        </div>
      </div>

      {p.refunded > 0 && (
        <div role="status" className="flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>No approved work: student pool refunded to sponsor (<MoneyText amount={p.refunded} />).</span>
        </div>
      )}

      {mine && (
        <div role="status" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-800">
          You earned <MoneyText amount={mine.amount} className="font-semibold" />
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Budget" amount={p.budget} />
        <Stat label="Student pool" amount={p.student_pool} />
        <Stat label="Researcher pool" amount={p.researcher_pool} />
        <Stat label="Project fund" amount={p.project_fund} />
        {p.refunded > 0 && <Stat label="Refunded" amount={p.refunded} />}
      </div>

      <section className="card">
        <DonutChart
          data={donutData(p.student_pool, p.researcher_pool, p.project_fund)}
          centerLabel="Total budget"
          centerValue={inr(p.budget)}
          size={200}
          formatValue={inr}
        />
      </section>

      <section className="card space-y-3">
        <h3 className="section-title">Researchers</h3>
        <div className="overflow-x-auto">
          <table className="table-clean w-full min-w-[420px] text-left text-sm">
            <thead>
              <tr><th>Name</th><th>Role</th><th>Share</th><th>Amount</th></tr>
            </thead>
            <tbody>
              {p.researchers.map((r) => (
                <tr key={r.researcher_id}>
                  <td>{r.name}</td>
                  <td>{r.role === "lead" ? "Lead" : "Researcher"}</td>
                  <td className="tabular-nums">{Math.round(r.share_pct * 100) / 100}%</td>
                  <td><MoneyText amount={r.amount} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card space-y-3">
        <h3 className="section-title">Students</h3>
        {p.students.length === 0 ? (
          <p className="muted">This project had no students.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-clean w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr>
                  <th>Student</th><th>Submitted</th><th>Approved</th><th>Files</th><th>Approval</th>
                  <th>Quality</th><th>Share</th><th>Amount</th><th>Project score</th><th>Rating change</th>
                </tr>
              </thead>
              <tbody>
                {p.students.map((s, i) => (
                  <tr key={s.student_id} className={s.student_id === user?.id ? "bg-indigo-50" : undefined}>
                    <td className="font-medium text-slate-900">
                      {s.name}
                      {s.status === "removed" && <span className="badge ml-2 bg-slate-100 text-slate-600">Removed</span>}
                      {s.student_id === user?.id && <span className="ml-1 text-xs text-indigo-600">(you)</span>}
                    </td>
                    <td className="tabular-nums">{s.submitted}</td>
                    <td className="tabular-nums">{s.approved}</td>
                    <td className="tabular-nums">{s.files_count}</td>
                    <td className="tabular-nums">{pctLabel(s.approval_ratio)}</td>
                    <td className="tabular-nums">{pctLabel(s.impact)}</td>
                    <td className="tabular-nums">{Math.round(s.share_pct * 10) / 10}%</td>
                    <td><MoneyText amount={s.amount} /></td>
                    <td><StarRating value={s.project_score} size="sm" /></td>
                    <td>
                      <FadeIn delayMs={i * 120}>
                        <div className="flex items-center gap-1.5">
                          <StarRating value={s.old_rating} size="sm" />
                          <span className="text-slate-400" aria-label="changed to">&rarr;</span>
                          <StarRating value={s.new_final_rating} size="sm" showValue />
                        </div>
                      </FadeIn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
          share = approved &times; (0.5 &times; approval ratio + 0.5 &times; quality) / total. Copied work counts
          for nothing.
        </p>
      </section>

      <section className="card space-y-3">
        <h3 className="section-title">Transactions</h3>
        <div className="overflow-x-auto">
          <table className="table-clean w-full min-w-[480px] text-left text-sm">
            <thead>
              <tr><th>Name</th><th>Role</th><th>Kind</th><th className="text-right">Amount</th></tr>
            </thead>
            <tbody>
              {p.transactions.map((t, i) => (
                <tr key={`${t.user_id}-${t.kind}-${i}`}>
                  <td>{t.name}</td>
                  <td className="capitalize">{t.role}</td>
                  <td>{KIND_LABEL[t.kind]}</td>
                  <td className="text-right"><MoneyText amount={t.amount} /></td>
                </tr>
              ))}
              <tr className="font-semibold">
                <td colSpan={3}>Total</td>
                <td className="text-right"><MoneyText amount={ledgerTotal} /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
