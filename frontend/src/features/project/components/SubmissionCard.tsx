"use client";

import { ReactNode, useState } from "react";
import { ChevronDown, ChevronRight, Files } from "lucide-react";
import { FileExplorer, OriginalityBadge, ScoreRing, StatusBadge, UserAvatar } from "@/components/common";
import { timeAgo } from "@/components/common/format";
import type { SubmissionOut } from "@/lib/types";
import { downloadFile, loadContent, loadVersions } from "./fileApi";
import { qualityValue } from "./format";

interface Props {
  submission: SubmissionOut;
  isResearcher: boolean;
  isSponsor: boolean;
  actions?: ReactNode;
}

export default function SubmissionCard({ submission: s, isResearcher, isSponsor, actions }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <article className="card space-y-3">
      <div className="flex items-start gap-3">
        <UserAvatar name={s.student_name} size="sm" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-900">{s.student_name}</p>
          <p className="help">{timeAgo(s.created_at)}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <OriginalityBadge originality={s.originality} />
          <StatusBadge status={s.status} />
        </div>
      </div>

      {s.originality === "copied" && (isResearcher || isSponsor) && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">
          Copied work detected in this submission. It counts for nothing in the payout.
        </div>
      )}

      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-sm font-semibold text-slate-900">{s.commit_msg}</p>
          {s.description && <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-600">{s.description}</p>}
        </div>
        {isResearcher &&
          (s.ai_quality_score === null ? (
            <span className="help shrink-0 italic">scoring...</span>
          ) : (
            <ScoreRing value={qualityValue(s.ai_quality_score)} size={44} label="AI quality" />
          ))}
      </div>

      {s.reviewer_feedback && (
        <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
          <p className="help font-medium uppercase tracking-wide">Reviewer feedback</p>
          <p className="mt-1 whitespace-pre-wrap break-words">{s.reviewer_feedback}</p>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          disabled={s.files.length === 0}
          className="btn btn-ghost btn-sm"
        >
          {open ? <ChevronDown className="h-4 w-4" aria-hidden="true" /> : <ChevronRight className="h-4 w-4" aria-hidden="true" />}
          <Files className="h-4 w-4" aria-hidden="true" />
          {s.files.length} {s.files.length === 1 ? "file" : "files"}
        </button>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>

      {open && (
        <FileExplorer
          files={s.files}
          loadContent={loadContent}
          loadVersions={loadVersions}
          onDownload={downloadFile}
          emptyText="No files attached."
        />
      )}
    </article>
  );
}
