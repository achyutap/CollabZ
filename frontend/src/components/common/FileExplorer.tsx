"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ChevronDown, ChevronRight, Download, File as FileIcon, Folder, FolderOpen } from "lucide-react";
import clsx from "clsx";
import type { FileContent, FileOut } from "@/lib/types";
import { Spinner } from "./Spinner";
import { formatDate, formatSize } from "./format";

interface FileExplorerProps {
  files: FileOut[];
  loadContent: (file: FileOut) => Promise<FileContent>;
  onDownload?: (file: FileOut) => void;
  loadVersions?: (file: FileOut) => Promise<FileOut[]>;
  renderBadges?: (file: FileOut) => ReactNode;
  renderActions?: (file: FileOut) => ReactNode;
  selectable?: boolean;
  selectedIds?: string[];
  onSelectionChange?: (ids: string[]) => void;
  emptyText?: string;
}

interface TreeNode {
  name: string;
  path: string;
  folders: TreeNode[];
  files: FileOut[];
}

function buildTree(files: FileOut[]): TreeNode {
  const root: TreeNode = { name: "", path: "", folders: [], files: [] };
  for (const f of files) {
    let parts = f.path.split("/").filter(Boolean);
    if (parts.length === 0) parts = [f.name];
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      let child = node.folders.find((x) => x.name === parts[i]);
      if (!child) {
        child = { name: parts[i], path: parts.slice(0, i + 1).join("/"), folders: [], files: [] };
        node.folders.push(child);
      }
      node = child;
    }
    node.files.push(f);
  }
  const sort = (n: TreeNode): void => {
    n.folders.sort((a, b) => a.name.localeCompare(b.name));
    n.files.sort((a, b) => a.name.localeCompare(b.name));
    n.folders.forEach(sort);
  };
  sort(root);
  return root;
}

function collectFiles(node: TreeNode): FileOut[] {
  return [...node.files, ...node.folders.flatMap(collectFiles)];
}

type ContentState =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "ready"; data: FileContent };

export function FileExplorer({
  files,
  loadContent,
  onDownload,
  loadVersions,
  renderBadges,
  renderActions,
  selectable = false,
  selectedIds = [],
  onSelectionChange,
  emptyText = "No files yet.",
}: FileExplorerProps) {
  const tree = useMemo(() => buildTree(files), [files]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [viewId, setViewId] = useState<string | null>(null);
  const [versions, setVersions] = useState<FileOut[] | null>(null);
  const [versionId, setVersionId] = useState<string | null>(null);
  const [content, setContent] = useState<ContentState>({ state: "idle" });

  const loadContentRef = useRef(loadContent);
  const loadVersionsRef = useRef(loadVersions);
  useEffect(() => {
    loadContentRef.current = loadContent;
    loadVersionsRef.current = loadVersions;
  });

  const baseFile = files.find((f) => f.id === viewId) ?? null;
  const baseId = baseFile?.id ?? null;
  const viewed = (versions && versionId ? versions.find((v) => v.id === versionId) : undefined) ?? baseFile;
  const viewedId = viewed?.id ?? null;
  const viewedIsText = viewed?.is_text ?? false;

  useEffect(() => {
    setVersions(null);
    setVersionId(null);
    const fn = loadVersionsRef.current;
    const file = files.find((f) => f.id === baseId);
    if (!fn || !file) return;
    let cancelled = false;
    fn(file)
      .then((v) => {
        if (!cancelled) {
          setVersions(v);
          setVersionId(file.id);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseId]);

  useEffect(() => {
    if (!viewedId || !viewedIsText) {
      setContent({ state: "idle" });
      return;
    }
    const target = (versions && versions.find((v) => v.id === viewedId)) ?? files.find((f) => f.id === viewedId);
    if (!target) return;
    let cancelled = false;
    setContent({ state: "loading" });
    loadContentRef
      .current(target)
      .then((data) => {
        if (!cancelled) setContent({ state: "ready", data });
      })
      .catch((e: unknown) => {
        if (!cancelled) setContent({ state: "error", message: e instanceof Error ? e.message : "Could not load file" });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewedId, viewedIsText]);

  if (files.length === 0) {
    return <p className="muted rounded-2xl border border-dashed border-slate-300 bg-white py-10 text-center">{emptyText}</p>;
  }

  const toggleFolder = (path: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });

  const setSelection = (ids: string[], on: boolean) => {
    if (!onSelectionChange) return;
    const set = new Set(selectedIds);
    ids.forEach((id) => (on ? set.add(id) : set.delete(id)));
    onSelectionChange(Array.from(set));
  };

  const renderNode = (node: TreeNode, depth: number): ReactNode => (
    <ul role={depth === 0 ? "tree" : "group"}>
      {node.folders.map((folder) => {
        const isCollapsed = collapsed.has(folder.path);
        const all = collectFiles(folder);
        const allSelected = all.length > 0 && all.every((f) => selectedIds.includes(f.id));
        return (
          <li key={folder.path} role="treeitem" aria-expanded={!isCollapsed}>
            <div className="flex items-center rounded-lg hover:bg-slate-50" style={{ paddingLeft: depth * 14 }}>
              {selectable && (
                <input type="checkbox" aria-label={`Select folder ${folder.name}`} checked={allSelected} onChange={(e) => setSelection(all.map((f) => f.id), e.target.checked)} className="ml-1 h-4 w-4 accent-indigo-600" />
              )}
              <button type="button" onClick={() => toggleFolder(folder.path)} className="flex min-w-0 flex-1 items-center gap-1.5 px-2 py-1.5 text-left text-sm text-slate-800">
                {isCollapsed ? <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" aria-hidden /> : <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />}
                {isCollapsed ? <Folder className="h-4 w-4 shrink-0 text-indigo-400" aria-hidden /> : <FolderOpen className="h-4 w-4 shrink-0 text-indigo-500" aria-hidden />}
                <span className="truncate font-medium">{folder.name}</span>
              </button>
            </div>
            {!isCollapsed && renderNode(folder, depth + 1)}
          </li>
        );
      })}
      {node.files.map((f) => (
        <li key={f.id} role="treeitem" aria-selected={f.id === viewId}>
          <div className={clsx("flex items-center rounded-lg", f.id === viewId ? "bg-indigo-50" : "hover:bg-slate-50")} style={{ paddingLeft: depth * 14 }}>
            {selectable && (
              <input type="checkbox" aria-label={`Select ${f.name}`} checked={selectedIds.includes(f.id)} onChange={(e) => setSelection([f.id], e.target.checked)} className="ml-1 h-4 w-4 accent-indigo-600" />
            )}
            <button
              type="button"
              onClick={() => setViewId(f.id)}
              className="flex min-w-0 flex-1 items-center gap-1.5 px-2 py-1.5 text-left text-sm text-slate-700"
            >
              <span className="w-4 shrink-0" aria-hidden />
              <FileIcon className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
              <span className="truncate">{f.name}</span>
            </button>
            {renderBadges && <span className="mr-2 flex shrink-0 items-center gap-1">{renderBadges(f)}</span>}
          </div>
        </li>
      ))}
    </ul>
  );

  const segments = viewed ? viewed.path.split("/").filter(Boolean) : [];

  return (
    <div className="grid gap-4 md:grid-cols-[18rem_minmax(0,1fr)]">
      <div className="max-h-96 overflow-auto rounded-2xl border border-slate-200 bg-white p-2 md:max-h-[36rem]">{renderNode(tree, 0)}</div>

      <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {!viewed ? (
          <p className="muted flex h-full min-h-[12rem] items-center justify-center p-6 text-center">Select a file to view it.</p>
        ) : (
          <>
            <div className="space-y-2 border-b border-slate-200 bg-slate-50 px-4 py-3">
              <nav aria-label="File path" className="flex flex-wrap items-center gap-1 font-mono text-xs text-slate-500">
                <span>root</span>
                {segments.map((seg, i) => (
                  <span key={`${seg}-${i}`} className="flex items-center gap-1">
                    <span aria-hidden>/</span>
                    <span className={i === segments.length - 1 ? "font-semibold text-slate-900" : ""}>{seg}</span>
                  </span>
                ))}
              </nav>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-slate-500">
                <span>{formatSize(viewed.size)}</span>
                <span>by {viewed.author_name}</span>
                <span>{formatDate(viewed.created_at)}</span>
                {versions && versions.length > 1 && (
                  <label className="flex items-center gap-1.5">
                    <span className="sr-only">Version</span>
                    <select value={versionId ?? ""} onChange={(e) => setVersionId(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700">
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          v{v.version} · {formatDate(v.created_at)}
                          {v.id === baseId ? " (latest)" : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {renderBadges?.(viewed)}
                <span className="ml-auto flex items-center gap-2">
                  {renderActions?.(viewed)}
                  {onDownload && (
                    <button type="button" onClick={() => onDownload(viewed)} className="btn btn-secondary btn-sm">
                      <Download className="h-3.5 w-3.5" aria-hidden /> Download
                    </button>
                  )}
                </span>
              </div>
            </div>

            {!viewed.is_text ? (
              <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
                <FileIcon className="h-8 w-8 text-slate-300" aria-hidden />
                <p className="font-medium text-slate-700">Binary file</p>
                <p className="muted">{formatSize(viewed.size)} · preview not available</p>
                {onDownload && (
                  <button type="button" onClick={() => onDownload(viewed)} className="btn btn-primary btn-sm">
                    <Download className="h-3.5 w-3.5" aria-hidden /> Download
                  </button>
                )}
              </div>
            ) : content.state === "loading" || content.state === "idle" ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : content.state === "error" ? (
              <p className="px-6 py-10 text-center text-sm text-red-600">{content.message}</p>
            ) : content.data.content === null ? (
              <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
                <p className="muted">This file is too large to preview.</p>
                {onDownload && (
                  <button type="button" onClick={() => onDownload(viewed)} className="btn btn-primary btn-sm">
                    <Download className="h-3.5 w-3.5" aria-hidden /> Download
                  </button>
                )}
              </div>
            ) : (
              <div>
                <div className="max-h-[32rem] overflow-auto">
                  <table className="w-full border-collapse font-mono text-xs leading-5">
                    <tbody>
                      {content.data.content.split("\n").map((line, i) => (
                        <tr key={i} className="hover:bg-slate-50">
                          <td className="sticky left-0 w-12 select-none bg-slate-50 px-3 text-right align-top text-slate-400">{i + 1}</td>
                          <td className="whitespace-pre px-3 text-slate-800">{line === "" ? " " : line}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {content.data.truncated && <p className="border-t border-slate-200 bg-amber-50 px-4 py-2 text-xs text-amber-700">File truncated. Download it to see everything.</p>}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
