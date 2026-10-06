"use client";

import { DragEvent, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { File as FileIcon, FolderPlus, UploadCloud, X } from "lucide-react";

export interface PickedFile {
  file: File;
  path: string;
}

export const MAX_FILES = 30;
export const MAX_FILE_BYTES = 5 * 1024 * 1024;
export const MAX_TOTAL_BYTES = 25 * 1024 * 1024;

function pathOf(f: File): string {
  return (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name;
}

function sizeLabel(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

function readAll(reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> {
  return new Promise((resolve, reject) => {
    const out: FileSystemEntry[] = [];
    const next = () =>
      reader.readEntries((batch) => {
        if (batch.length === 0) resolve(out);
        else {
          batch.forEach((b) => out.push(b));
          next();
        }
      }, reject);
    next();
  });
}

async function walk(entry: FileSystemEntry, acc: PickedFile[]): Promise<void> {
  if (entry.isFile) {
    const f = await new Promise<File>((res, rej) => (entry as FileSystemFileEntry).file(res, rej));
    acc.push({ file: f, path: entry.fullPath.replace(/^\//, "") });
  } else if (entry.isDirectory) {
    const children = await readAll((entry as FileSystemDirectoryEntry).createReader());
    for (const c of children) await walk(c, acc);
  }
}

interface Props {
  entries: PickedFile[];
  onChange: (e: PickedFile[]) => void;
  disabled?: boolean;
}

export default function FilePicker({ entries, onChange, disabled }: Props) {
  const filesRef = useRef<HTMLInputElement>(null);
  const dirRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    dirRef.current?.setAttribute("webkitdirectory", "");
  }, []);

  const total = entries.reduce((s, e) => s + e.file.size, 0);

  function add(incoming: PickedFile[]) {
    const map = new Map<string, PickedFile>();
    entries.forEach((e) => map.set(e.path, e));
    const notes: string[] = [];
    let runningTotal = total;
    incoming.forEach((inc) => {
      if (inc.file.size > MAX_FILE_BYTES) {
        notes.push(`${inc.path} is over 5 MB`);
        return;
      }
      const existing = map.get(inc.path);
      const delta = inc.file.size - (existing ? existing.file.size : 0);
      if (!existing && map.size >= MAX_FILES) {
        notes.push(`Limit of ${MAX_FILES} files reached`);
        return;
      }
      if (runningTotal + delta > MAX_TOTAL_BYTES) {
        notes.push("Total size limit of 25 MB reached");
        return;
      }
      runningTotal += delta;
      map.set(inc.path, inc);
    });
    setProblem(notes.length ? Array.from(new Set(notes)).slice(0, 3).join(". ") + "." : null);
    onChange(Array.from(map.values()));
  }

  function fromList(list: FileList | null) {
    if (!list) return;
    add(Array.from(list).map((f) => ({ file: f, path: pathOf(f) })));
  }

  async function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const items = Array.from(e.dataTransfer.items ?? []);
    const roots: FileSystemEntry[] = [];
    items.forEach((it) => {
      const entry = typeof it.webkitGetAsEntry === "function" ? it.webkitGetAsEntry() : null;
      if (entry) roots.push(entry);
    });
    if (roots.length === 0) {
      fromList(e.dataTransfer.files);
      return;
    }
    const acc: PickedFile[] = [];
    try {
      for (const r of roots) await walk(r, acc);
    } catch {
      setProblem("Could not read the dropped items.");
      return;
    }
    add(acc);
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => void onDrop(e)}
        className={clsx(
          "flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed p-6 text-center",
          dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300"
        )}
      >
        <UploadCloud className="h-7 w-7 text-slate-400" aria-hidden="true" />
        <p className="muted">Drag files or folders here, or choose below</p>
        <div className="flex flex-wrap justify-center gap-2">
          <button type="button" disabled={disabled} onClick={() => filesRef.current?.click()} className="btn btn-secondary btn-sm">
            <FileIcon className="h-4 w-4" aria-hidden="true" /> Choose files
          </button>
          <button type="button" disabled={disabled} onClick={() => dirRef.current?.click()} className="btn btn-secondary btn-sm">
            <FolderPlus className="h-4 w-4" aria-hidden="true" /> Add folder
          </button>
        </div>
        <input
          ref={filesRef}
          type="file"
          multiple
          className="sr-only"
          tabIndex={-1}
          aria-label="Choose files"
          onChange={(e) => {
            fromList(e.target.files);
            e.target.value = "";
          }}
        />
        <input
          ref={dirRef}
          type="file"
          multiple
          className="sr-only"
          tabIndex={-1}
          aria-label="Choose a folder"
          onChange={(e) => {
            fromList(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <p className="help">
        {entries.length}/{MAX_FILES} files · {sizeLabel(total)} of 25 MB · max 5 MB per file
      </p>
      {problem && (
        <p role="alert" className="error-text">
          {problem}
        </p>
      )}

      {entries.length > 0 && (
        <ul className="max-h-56 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
          {entries.map((e) => (
            <li key={e.path} className="flex items-center gap-2 px-3 py-2 text-sm">
              <FileIcon className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-800">{e.path}</span>
              <span className="shrink-0 text-xs text-slate-400">{sizeLabel(e.file.size)}</span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onChange(entries.filter((x) => x.path !== e.path))}
                aria-label={`Remove ${e.path}`}
                className="btn-ghost rounded-md p-1"
              >
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
