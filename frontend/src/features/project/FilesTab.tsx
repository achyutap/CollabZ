"use client";

import { useState } from "react";
import { Globe, Lock } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { FileOut } from "@/lib/types";
import { FileExplorer, OriginalityBadge, Spinner, StatusBadge } from "@/components/common";
import { isProjectResearcher, TabProps } from "./components/tabTypes";
import { downloadFile, loadContent, loadVersions } from "./components/fileApi";
import { useErrorToast } from "./components/hooks";
import { errMsg } from "./components/format";

export default function FilesTab({ projectId, project }: TabProps) {
  const files = useFetch<FileOut[]>(`/projects/${projectId}/files`);
  useErrorToast(files.error);
  const canPublish = isProjectResearcher(project);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function setVisibility(ids: string[], isPublic: boolean) {
    if (ids.length === 0) return;
    setBusy(true);
    try {
      await api.post<FileOut[]>(`/projects/${projectId}/files/visibility`, { file_ids: ids, is_public: isPublic });
      toast.success(isPublic ? "Files are now public" : "Files are now private");
      setSelected([]);
      await files.refetch();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  async function toggleOne(f: FileOut) {
    setBusy(true);
    try {
      await api.patch<FileOut>(`/files/${f.id}/visibility`, { is_public: !f.is_public });
      await files.refetch();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  if (files.loading && !files.data) {
    return <div className="flex justify-center py-10"><Spinner /></div>;
  }

  return (
    <div className="space-y-4">
      {canPublish && (
        <div className="card space-y-3">
          <p className="muted">
            Files are <strong>private</strong> by default: only people in this project can see them. You can make an
            approved, original file <strong>public</strong>, so any logged-in user can view it. A project with at
            least one public file appears in Explore and on profiles.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" disabled={busy || selected.length === 0} onClick={() => void setVisibility(selected, true)} className="btn btn-primary btn-sm">
              <Globe className="h-4 w-4" aria-hidden="true" /> Make public
            </button>
            <button type="button" disabled={busy || selected.length === 0} onClick={() => void setVisibility(selected, false)} className="btn btn-secondary btn-sm">
              <Lock className="h-4 w-4" aria-hidden="true" /> Make private
            </button>
            <span className="help">{selected.length} selected</span>
          </div>
        </div>
      )}

      <div className="card">
        <FileExplorer
          files={files.data ?? []}
          loadContent={loadContent}
          loadVersions={loadVersions}
          onDownload={downloadFile}
          selectable={canPublish}
          selectedIds={selected}
          onSelectionChange={setSelected}
          emptyText="No files have been submitted yet."
          renderBadges={(f) => (
            <span className="flex flex-wrap items-center gap-1.5">
              <span className="help">{f.author_name}</span>
              <StatusBadge status={f.status} />
              <span className={f.is_public ? "badge bg-sky-50 text-sky-700" : "badge bg-slate-100 text-slate-600"}>
                {f.is_public ? "Public" : "Private"}
              </span>
              <OriginalityBadge originality={f.originality} />
            </span>
          )}
          renderActions={
            canPublish
              ? (f) => (
                  <button type="button" disabled={busy} onClick={() => void toggleOne(f)} className="btn btn-ghost btn-sm">
                    {f.is_public ? "Make private" : "Make public"}
                  </button>
                )
              : undefined
          }
        />
      </div>
    </div>
  );
}
