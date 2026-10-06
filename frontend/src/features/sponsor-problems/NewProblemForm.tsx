"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { ProblemOut, WalletOut } from "@/lib/types";
import { SkillChip, MoneyText, PageHeader, DonutChart } from "@/components/common";
import { SKILLS, skillLabel } from "@/components/common/skills";
import { inr, msg } from "./util";

type Split = { s: number; r: number; p: number };
type Key = keyof Split;

function rebalance(cur: Split, key: Key, raw: number): Split {
  const v = Math.max(0, Math.min(100, Math.round(Number.isFinite(raw) ? raw : 0)));
  const [a, b] = (["s", "r", "p"] as Key[]).filter((k) => k !== key);
  const rest = 100 - v;
  const sum = cur[a] + cur[b];
  const na = sum === 0 ? Math.round(rest / 2) : Math.round((cur[a] / sum) * rest);
  return { ...cur, [key]: v, [a]: na, [b]: rest - na };
}

export default function NewProblemForm() {
  const router = useRouter();
  const wallet = useFetch<WalletOut>("/me/wallet");
  const [step, setStep] = useState<1 | 2>(1);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState("");
  const [split, setSplit] = useState<Split>({ s: 30, r: 70, p: 0 });
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<ProblemOut | null>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [toAdd, setToAdd] = useState("");

  const budgetNum = Number(budget);
  const budgetValid = budget.trim() !== "" && Number.isFinite(budgetNum) && budgetNum > 0;
  const balance = wallet.data?.balance;
  const errors = {
    title: title.trim().length < 3 || title.trim().length > 200 ? "Title must be 3-200 characters." : "",
    description: description.trim().length < 30 ? "Description must be at least 30 characters." : "",
    budget: !budgetValid ? "Enter a budget greater than 0." : balance !== undefined && budgetNum > balance ? `Budget exceeds your wallet balance (${inr(balance)}).` : "",
  };
  const hasError = Boolean(errors.title || errors.description || errors.budget);
  const amt = (pct: number) => (budgetValid ? (budgetNum * pct) / 100 : 0);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    if (hasError) return;
    setBusy(true);
    try {
      const p = await api.post<ProblemOut>("/problems", {
        title: title.trim(), description: description.trim(), budget: budgetNum,
        student_pct: split.s, researcher_pct: split.r, project_pct: split.p,
      });
      setProblem(p);
      setSkills(p.required_skills);
      setStep(2);
    } catch (err) {
      if (err instanceof ApiError && err.code === "INSUFFICIENT_FUNDS") toast.error("Insufficient wallet funds for this budget.");
      else toast.error(msg(err));
    } finally { setBusy(false); }
  }

  async function confirm() {
    if (!problem || skills.length < 1) return;
    setBusy(true);
    try {
      const same = [...skills].sort().join(",") === [...problem.required_skills].sort().join(",");
      if (!same) await api.patch<ProblemOut>(`/problems/${problem.id}/skills`, { required_skills: skills });
      router.push(`/sponsor/problems/${problem.id}/matches`);
    } catch (err) { toast.error(msg(err)); setBusy(false); }
  }

  const rows: { k: Key; label: string; color: string }[] = [
    { k: "s", label: "Students", color: "#4f46e5" },
    { k: "r", label: "Researchers", color: "#10b981" },
    { k: "p", label: "Project fund", color: "#f59e0b" },
  ];

  if (step === 2 && problem) {
    const available = SKILLS.filter((s) => !skills.includes(s.id));
    return (
      <div className="page max-w-2xl">
        <PageHeader title="Review extracted skills" description="These skills are used to match researchers. Add or remove as needed." />
        <div className="card space-y-4 p-5">
          <div className="flex flex-wrap gap-2" aria-label="Required skills">
            {skills.map((s) => (
              <SkillChip key={s} label={skillLabel(s)} variant="selected" onRemove={() => setSkills(skills.filter((x) => x !== s))} />
            ))}
          </div>
          {skills.length < 1 && <p className="error-text">At least one skill is required.</p>}
          <div className="flex gap-2">
            <label className="sr-only" htmlFor="add-skill">Add skill</label>
            <select id="add-skill" className="input" value={toAdd} onChange={(e) => setToAdd(e.target.value)}>
              <option value="">Add skill…</option>
              {available.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
            <button type="button" className="btn btn-secondary" disabled={!toAdd} onClick={() => { setSkills([...skills, toAdd]); setToAdd(""); }}>Add skill</button>
          </div>
          <button type="button" className="btn btn-primary w-full" disabled={busy || skills.length < 1} onClick={confirm}>
            {busy ? "Saving…" : "Confirm & find researchers"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page max-w-3xl">
      <PageHeader title="New problem" description="Describe the problem and decide how the budget is shared." />
      <form onSubmit={create} className="card space-y-5 p-5" noValidate>
        <div>
          <label className="label" htmlFor="title">Title</label>
          <input id="title" className="input" value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
          {submitted && errors.title && <p className="error-text">{errors.title}</p>}
        </div>
        <div>
          <label className="label" htmlFor="desc">Description</label>
          <textarea id="desc" className="input min-h-[140px]" value={description} onChange={(e) => setDescription(e.target.value)} />
          <p className="help">{description.trim().length} / 30 minimum characters</p>
          {submitted && errors.description && <p className="error-text">{errors.description}</p>}
        </div>
        <div>
          <label className="label" htmlFor="budget">Budget (₹)</label>
          <input id="budget" type="number" min={0} step="0.01" inputMode="decimal" className="input" value={budget} onChange={(e) => setBudget(e.target.value)} />
          <p className="help">Wallet balance: {balance === undefined ? "…" : <MoneyText amount={balance} />}</p>
          {(submitted || (budgetValid && balance !== undefined && budgetNum > balance)) && errors.budget && <p className="error-text">{errors.budget}</p>}
        </div>

        <fieldset className="space-y-4">
          <legend className="label">Budget split (always totals 100%)</legend>
          <div className="grid gap-5 md:grid-cols-2">
            <div className="space-y-4">
              {rows.map((r) => (
                <div key={r.k} className="space-y-1">
                  <div className="flex items-center justify-between gap-3">
                    <label htmlFor={`pct-${r.k}`} className="text-sm font-medium text-slate-700">{r.label} %</label>
                    <input id={`pct-${r.k}`} type="number" min={0} max={100} className="input w-20 text-right" value={split[r.k]} onChange={(e) => setSplit(rebalance(split, r.k, Number(e.target.value)))} />
                  </div>
                  <input type="range" min={0} max={100} aria-label={`${r.label} percentage`} className="w-full accent-indigo-600" value={split[r.k]} onChange={(e) => setSplit(rebalance(split, r.k, Number(e.target.value)))} />
                  <p className="help">{inr(amt(split[r.k]))}</p>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-center">
              <DonutChart
                size={170}
                centerLabel="Budget"
                centerValue={budgetValid ? inr(budgetNum) : "—"}
                data={rows.map((r) => ({ label: r.label, value: budgetValid ? amt(split[r.k]) : split[r.k], color: r.color }))}
                formatValue={(n) => (budgetValid ? inr(n) : `${n}%`)}
              />
            </div>
          </div>
          <p className="text-sm text-slate-600">{inr(amt(split.s))} to students, {inr(amt(split.r))} to researchers, {inr(amt(split.p))} project fund.</p>
        </fieldset>

        <button type="submit" className="btn btn-primary w-full" disabled={busy}>{busy ? "Posting…" : "Post problem & escrow budget"}</button>
      </form>
    </div>
  );
}
