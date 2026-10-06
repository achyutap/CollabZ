"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import type { ActivityItem, FileContent, FileOut } from "@/lib/types";
import {
  ConfirmDialog,
  CountBadge,
  DonutChart,
  EmptyState,
  FileExplorer,
  Logo,
  MoneyText,
  OriginalityBadge,
  PageHeader,
  ScoreRing,
  SkillChip,
  Spinner,
  StarRating,
  StatusBadge,
  Tabs,
  Timeline,
  UserAvatar,
  skillLabel,
} from "@/components/common";

const now = Date.now();
const ago = (mins: number): string => new Date(now - mins * 60000).toISOString();

function file(id: string, path: string, over: Partial<FileOut> = {}): FileOut {
  return {
    id,
    submission_id: "s1",
    project_id: "p1",
    path,
    name: path.split("/").pop() ?? path,
    size: 1200,
    content_type: "text/plain",
    is_text: true,
    version: 1,
    originality: "original",
    is_public: false,
    author_id: "u1",
    author_name: "Asha Rao",
    status: "approved",
    created_at: ago(300),
    ...over,
  };
}

const FILES: FileOut[] = [
  file("f1", "README.md"),
  file("f2", "src/app/main.py", { version: 2, is_public: true }),
  file("f3", "src/app/utils.py", { originality: "copied", status: "pending" }),
  file("f4", "data/model.bin", { is_text: false, content_type: "application/octet-stream", size: 482133 }),
  file("f5", "docs/notes/plan.txt"),
];

const SAMPLE: Record<string, string> = {
  f1: "# Demo project\n\nA sample README.\n",
  f2: "from fastapi import FastAPI\n\napp = FastAPI()\n\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n",
  f3: "def add(a, b):\n    return a + b\n",
  f5: "Phase 1: collect data\nPhase 2: train model\n",
};

const ACTIVITY: ActivityItem[] = [
  { id: "a1", type: "submission_approved", actor: { id: "u2", name: "Dr. Meera Nair", role: "researcher" }, message: "approved a submission", ref_id: "s1", meta: { submission_id: "s1", student_id: "u1", commit_msg: "Add data loader", file_count: 3, status: "approved" }, created_at: ago(12) },
  { id: "a2", type: "submission_created", actor: { id: "u1", name: "Asha Rao", role: "student" }, message: "submitted work", ref_id: "s1", meta: { submission_id: "s1", student_id: "u1", commit_msg: "Add data loader", file_count: 3, status: "pending" }, created_at: ago(95) },
  { id: "a3", type: "student_joined", actor: { id: "u1", name: "Asha Rao", role: "student" }, message: "joined as Python", ref_id: null, meta: {}, created_at: ago(60 * 26) },
  { id: "a4", type: "project_created", actor: { id: "u2", name: "Dr. Meera Nair", role: "researcher" }, message: "created the project", ref_id: null, meta: {}, created_at: ago(60 * 24 * 9) },
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card space-y-4">
      <h2 className="section-title">{title}</h2>
      {children}
    </section>
  );
}

export default function ComponentsShowcase() {
  const [tab, setTab] = useState("overview");
  const [dialog, setDialog] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

  const loadContent = async (f: FileOut): Promise<FileContent> => {
    await new Promise((r) => setTimeout(r, 300));
    const text = SAMPLE[f.id] ?? null;
    return { id: f.id, path: f.path, size: f.size, is_text: f.is_text, truncated: false, content: text };
  };

  return (
    <div className="page">
      <PageHeader title="Component showcase" description="Every shared CollabZ component with sample data." actions={<Logo />} />

      <Section title="Buttons & classes">
        <div className="flex flex-wrap gap-2">
          <button className="btn btn-primary">Primary</button>
          <button className="btn btn-secondary">Secondary</button>
          <button className="btn btn-danger">Danger</button>
          <button className="btn btn-ghost">Ghost</button>
          <button className="btn btn-primary btn-sm">Small</button>
          <button className="btn btn-primary" disabled>Disabled</button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="demo-input">Label</label>
            <input id="demo-input" className="input" placeholder="Input" />
            <p className="help">Helper text</p>
          </div>
          <div>
            <label className="label" htmlFor="demo-bad">With error</label>
            <input id="demo-bad" className="input !border-red-400" defaultValue="oops" />
            <p className="error-text">Something is wrong</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="table-clean">
            <thead><tr><th>Name</th><th>Role</th><th className="text-right">Amount</th></tr></thead>
            <tbody>
              <tr><td>Asha Rao</td><td><span className="badge bg-slate-100 text-slate-600 ring-slate-200">Student</span></td><td className="text-right"><MoneyText amount={12500} /></td></tr>
              <tr><td>Dr. Meera Nair</td><td><span className="badge bg-violet-50 text-violet-700 ring-violet-200">Researcher</span></td><td className="text-right"><MoneyText amount={40250.5} /></td></tr>
            </tbody>
          </table>
        </div>
        <hr className="divider" />
        <p className="muted">Muted text under a divider.</p>
      </Section>

      <Section title="StarRating, MoneyText, ScoreRing, Spinner, UserAvatar, CountBadge">
        <div className="flex flex-wrap items-center gap-6">
          <StarRating value={4.5} showValue />
          <StarRating value={3.2} size="sm" showValue />
          <StarRating value={null} />
          <MoneyText amount={500000} />
          <MoneyText amount={1234.5} />
          <ScoreRing value={0.82} label="Match" />
          <ScoreRing value={0.35} size={48} />
          <Spinner />
          <UserAvatar name="Asha Rao" size="sm" />
          <UserAvatar name="Dr. Meera Nair" />
          <UserAvatar name="Kiran" size="lg" />
          <span className="flex items-center gap-2">Requests <CountBadge count={3} /></span>
          <span className="flex items-center gap-2">Big <CountBadge count={150} /></span>
          <span className="flex items-center gap-2">Zero <CountBadge count={0} /></span>
        </div>
      </Section>

      <Section title="StatusBadge & OriginalityBadge">
        <div className="flex flex-wrap gap-2">
          {["open", "matched", "completed", "pending", "accepted", "declined", "expired", "active", "approved", "rejected", "clean", "suspicious", "likely_copied", "copied", "original", "removed", "blacklisted", "lead", "researcher"].map((s) => (
            <StatusBadge key={s} status={s} />
          ))}
        </div>
        <div className="flex gap-2">
          <OriginalityBadge originality="original" />
          <OriginalityBadge originality="copied" />
        </div>
      </Section>

      <Section title="SkillChip">
        <div className="flex flex-wrap gap-2">
          <SkillChip label={skillLabel("python")} />
          <SkillChip label={skillLabel("react")} variant="selected" onClick={() => undefined} />
          <SkillChip label={skillLabel("sql")} variant="matched" />
          <SkillChip label={skillLabel("iot")} variant="missing" />
          <SkillChip label={skillLabel("ml")} onRemove={() => undefined} />
        </div>
      </Section>

      <Section title="Tabs">
        <Tabs
          tabs={[
            { id: "overview", label: "Overview" },
            { id: "work", label: "Work", count: 4 },
            { id: "files", label: "Files" },
          ]}
          active={tab}
          onChange={setTab}
        />
        <p className="muted">Active tab: {tab}</p>
      </Section>

      <Section title="DonutChart">
        <DonutChart
          data={[
            { label: "Students", value: 60000 },
            { label: "Researchers", value: 30000 },
            { label: "Project fund", value: 10000 },
          ]}
          centerLabel="Total budget"
          centerValue="₹1,00,000"
          formatValue={(n) => `₹${n.toLocaleString("en-IN")}`}
        />
      </Section>

      <Section title="EmptyState & ConfirmDialog">
        <EmptyState title="Nothing here yet" description="Items will appear once they exist." action={<button className="btn btn-primary btn-sm">Create one</button>} />
        <button className="btn btn-danger" onClick={() => setDialog(true)}>Open confirm dialog</button>
        <ConfirmDialog
          open={dialog}
          onOpenChange={setDialog}
          title="Remove student?"
          description="They will still be paid for approved work."
          confirmLabel="Remove"
          destructive
          onConfirm={() => new Promise<void>((r) => setTimeout(r, 800))}
        />
      </Section>

      <Section title="Timeline">
        <Timeline items={ACTIVITY} onActorClick={() => undefined} />
      </Section>

      <Section title="FileExplorer">
        <FileExplorer
          files={FILES}
          loadContent={loadContent}
          onDownload={() => undefined}
          loadVersions={async (f) => [f, { ...f, id: `${f.id}-v0`, version: Math.max(1, f.version - 1), created_at: ago(2000) }]}
          renderBadges={(f) => <OriginalityBadge originality={f.originality} />}
          renderActions={(f) => (f.is_public ? <StatusBadge status="approved" /> : null)}
          selectable
          selectedIds={selected}
          onSelectionChange={setSelected}
        />
        <p className="help">Selected: {selected.length}</p>
      </Section>
    </div>
  );
}
