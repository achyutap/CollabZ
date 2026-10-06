"use client";
import { useState } from "react";
import { Pencil } from "lucide-react";
import { RowsEditor, TagInput } from "./editors";
import type { FieldDef, Row } from "./editors";

export type SectionCfg =
  | { kind: "fields"; title: string; fields: FieldDef[] }
  | { kind: "rows"; title: string; key: string; fields: FieldDef[]; addLabel: string }
  | { kind: "tags"; title: string; key: string; placeholder: string };

type Details = Record<string, unknown>;

function toRows(v: unknown, fields: FieldDef[]): Row[] {
  if (!Array.isArray(v)) return [];
  return v.map((item) => {
    const o = (item && typeof item === "object" ? item : {}) as Record<string, unknown>;
    const r: Row = {};
    fields.forEach((f) => { const x = o[f.key]; r[f.key] = x === null || x === undefined ? "" : String(x); });
    return r;
  });
}
function toTags(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}
function str(v: unknown): string { return typeof v === "string" ? v : v === null || v === undefined ? "" : String(v); }

export function RowsView({ rows, fields }: { rows: Row[]; fields: FieldDef[] }) {
  return (
    <ul className="space-y-3">
      {rows.map((r, i) => {
        const head = r[fields[0].key];
        const sub = fields.slice(1).filter((f) => f.key !== "url").map((f) => r[f.key]).filter(Boolean).join(" · ");
        return (
          <li key={i}>
            <p className="text-sm font-medium text-slate-900">{head}</p>
            {sub && <p className="muted text-sm">{sub}</p>}
            {r.url && /^https?:\/\//i.test(r.url) && <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-sm text-indigo-600 hover:underline">Link</a>}
          </li>
        );
      })}
    </ul>
  );
}

export default function DetailSection({ cfg, details, isMe, onSave }: { cfg: SectionCfg; details: Details; isMe: boolean; onSave: (patch: Details) => Promise<boolean> }) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [fieldDraft, setFieldDraft] = useState<Record<string, string>>({});
  const [rowDraft, setRowDraft] = useState<Row[]>([]);
  const [tagDraft, setTagDraft] = useState<string[]>([]);

  const fieldVals: Record<string, string> = {};
  const rows: Row[] = cfg.kind === "rows" ? toRows(details[cfg.key], cfg.fields) : [];
  const tags: string[] = cfg.kind === "tags" ? toTags(details[cfg.key]) : [];
  if (cfg.kind === "fields") cfg.fields.forEach((f) => { fieldVals[f.key] = str(details[f.key]); });

  const empty = cfg.kind === "fields" ? cfg.fields.every((f) => !fieldVals[f.key]) : cfg.kind === "rows" ? rows.length === 0 : tags.length === 0;
  if (!isMe && empty) return null;

  function start() {
    setFieldDraft(fieldVals);
    setRowDraft(rows);
    setTagDraft(tags);
    setEditing(true);
  }
  async function save() {
    setSaving(true);
    let patch: Details = {};
    if (cfg.kind === "fields") patch = { ...fieldDraft };
    else if (cfg.kind === "tags") patch = { [cfg.key]: tagDraft };
    else {
      const first = cfg.fields[0].key;
      patch = {
        [cfg.key]: rowDraft.filter((r) => (r[first] ?? "").trim() !== "").map((r) => {
          const o: Record<string, string | number> = {};
          cfg.fields.forEach((f) => { const v = (r[f.key] ?? "").trim(); o[f.key] = /year$/.test(f.key) && /^\d+$/.test(v) ? Number(v) : v; });
          return o;
        }),
      };
    }
    const ok = await onSave(patch);
    setSaving(false);
    if (ok) setEditing(false);
  }

  return (
    <section className="card space-y-3 p-5" aria-label={cfg.title}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="section-title">{cfg.title}</h2>
        {isMe && !editing && <button className="btn btn-ghost btn-sm" onClick={start}><Pencil className="h-4 w-4" aria-hidden /> Edit</button>}
      </div>
      {editing ? (
        <div className="space-y-4">
          {cfg.kind === "fields" && (
            <div className="grid gap-3 sm:grid-cols-2">
              {cfg.fields.map((f) => (
                <div key={f.key}>
                  <label className="label" htmlFor={`f-${f.key}`}>{f.label}</label>
                  <input id={`f-${f.key}`} className="input" value={fieldDraft[f.key] ?? ""} onChange={(e) => setFieldDraft({ ...fieldDraft, [f.key]: e.target.value })} />
                </div>
              ))}
            </div>
          )}
          {cfg.kind === "rows" && <RowsEditor rows={rowDraft} fields={cfg.fields} onChange={setRowDraft} addLabel={cfg.addLabel} />}
          {cfg.kind === "tags" && <TagInput label={cfg.title} values={tagDraft} onChange={setTagDraft} placeholder={cfg.placeholder} />}
          <div className="flex gap-2">
            <button className="btn btn-primary btn-sm" disabled={saving} onClick={save}>{saving ? "Saving…" : "Save"}</button>
            <button className="btn btn-secondary btn-sm" disabled={saving} onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      ) : empty ? (
        <p className="muted text-sm">Nothing added yet.</p>
      ) : cfg.kind === "fields" ? (
        <dl className="grid gap-3 sm:grid-cols-2">
          {cfg.fields.filter((f) => fieldVals[f.key]).map((f) => (
            <div key={f.key}><dt className="muted text-xs">{f.label}</dt><dd className="text-sm">{fieldVals[f.key]}</dd></div>
          ))}
        </dl>
      ) : cfg.kind === "rows" ? (
        <RowsView rows={rows} fields={cfg.fields} />
      ) : (
        <div className="flex flex-wrap gap-1.5">{tags.map((t) => <span key={t} className="badge">{t}</span>)}</div>
      )}
    </section>
  );
}
