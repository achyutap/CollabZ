"use client";
import { useId, useState } from "react";
import { Plus, X } from "lucide-react";

export type Row = Record<string, string>;
export type FieldDef = { key: string; label: string };

export function TagInput({ label, values, onChange, placeholder }: { label: string; values: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  const id = useId();
  const [text, setText] = useState("");
  function add() {
    const t = text.trim();
    if (t && !values.includes(t)) onChange([...values, t]);
    setText("");
  }
  return (
    <div className="space-y-2">
      <label className="label" htmlFor={id}>{label}</label>
      <div className="flex flex-wrap gap-1.5">
        {values.map((v) => (
          <span key={v} className="badge gap-1">{v}
            <button type="button" aria-label={`Remove ${v}`} onClick={() => onChange(values.filter((x) => x !== v))}><X className="h-3 w-3" /></button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input id={id} className="input" value={text} placeholder={placeholder} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} />
        <button type="button" className="btn btn-secondary" onClick={add}>Add</button>
      </div>
    </div>
  );
}

export function RowsEditor({ rows, fields, onChange, addLabel }: { rows: Row[]; fields: FieldDef[]; onChange: (r: Row[]) => void; addLabel: string }) {
  const uid = useId();
  function set(i: number, key: string, value: string) {
    onChange(rows.map((r, idx) => (idx === i ? { ...r, [key]: value } : r)));
  }
  function add() {
    const blank: Row = {};
    fields.forEach((f) => { blank[f.key] = ""; });
    onChange([...rows, blank]);
  }
  return (
    <div className="space-y-3">
      {rows.map((r, i) => (
        <div key={i} className="relative grid gap-3 rounded-xl border border-slate-200 p-3 sm:grid-cols-2">
          {fields.map((f) => (
            <div key={f.key}>
              <label className="label" htmlFor={`${uid}-${i}-${f.key}`}>{f.label}</label>
              <input id={`${uid}-${i}-${f.key}`} className="input" value={r[f.key] ?? ""} onChange={(e) => set(i, f.key, e.target.value)} />
            </div>
          ))}
          <button type="button" className="btn btn-ghost btn-sm sm:col-span-2 sm:justify-self-end" onClick={() => onChange(rows.filter((_, idx) => idx !== i))}>Remove entry</button>
        </div>
      ))}
      <button type="button" className="btn btn-secondary btn-sm" onClick={add}><Plus className="h-4 w-4" aria-hidden /> {addLabel}</button>
    </div>
  );
}
