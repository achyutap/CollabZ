"use client";

import { FormEvent, useMemo, useState } from "react";
import clsx from "clsx";
import { ClipboardList } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { SubmissionOut } from "@/lib/types";
import { EmptyState, OriginalityBadge, Spinner } from "@/components/common";
import { isProjectResearcher, TabProps } from "./components/tabTypes";
import SubmissionCard from "./components/SubmissionCard";
import ReviewModal from "./components/ReviewModal";
import FilePicker, { PickedFile } from "./components/FilePicker";
import BlockedNotice from "./components/BlockedNotice";
import { useErrorToast } from "./components/hooks";
import { errMsg } from "./components/format";

export default function WorkTab({ projectId, role, project, refreshCounts }: TabProps) {
  const path = `/projects/${projectId}/submissions`;
  const feed = useFetch<SubmissionOut[]>(path, { intervalMs: 15000 });
  useErrorToast(feed.error);

  const isResearcher = isProjectResearcher(project);
  const isSponsor = project.my_role === "sponsor";

  const [person, setPerson] = useState("");
  const [status, setStatus] = useState("");
  const [reviewing, setReviewing] = useState<SubmissionOut | null>(null);
  const [busy, setBusy] = useState(false);

  const people = useMemo(() => {
    const m = new Map<string, string>();
    (feed.data ?? []).forEach((s) => m.set(s.student_id, s.student_name));
    return Array.from(m.entries());
  }, [feed.data]);

  const list = useMemo(
    () =>
      (feed.data ?? [])
        .filter((s) => (!person || s.student_id === person) && (!status || s.status === status))
        .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [feed.data, person, status]
  );

  async function review(approve: boolean, feedback: string, publicIds: string[]) {
    if (!reviewing) return;
    setBusy(true);
    try {
      await api.post<SubmissionOut>(`/submissions/${reviewing.id}/review`, {
        approve,
        feedback: feedback.trim() ? feedback.trim() : undefined,
        public_file_ids: approve && publicIds.length > 0 ? publicIds : undefined,
      });
      toast.success(approve ? "Submission approved" : "Submission rejected");
      setReviewing(null);
      await Promise.all([feed.refetch(), refreshCounts()]);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {role === "student" && project.my_role === "student" && (
        <SubmitCard
          projectId={projectId}
          completed={project.status === "completed"}
          onSubmitted={async () => {
            await Promise.all([feed.refetch(), refreshCounts()]);
          }}
        />
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="section-title">All submissions</h2>
          <div className="flex flex-wrap gap-3">
            <div>
              <label htmlFor="feed-person" className="label">Person</label>
              <select id="feed-person" value={person} onChange={(e) => setPerson(e.target.value)} className="input">
                <option value="">Everyone</option>
                {people.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="feed-status" className="label">Status</label>
              <select id="feed-status" value={status} onChange={(e) => setStatus(e.target.value)} className="input">
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>
        </div>

        {feed.loading && !feed.data ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : list.length === 0 ? (
          <EmptyState
            icon={<ClipboardList className="h-8 w-8" />}
            title="No submissions found"
            description={person || status ? "Try clearing the filters." : "Nobody has submitted work yet."}
          />
        ) : (
          <div className="space-y-4">
            {list.map((s) => (
              <SubmissionCard
                key={s.id}
                submission={s}
                isResearcher={isResearcher}
                isSponsor={isSponsor}
                actions={
                  project.can_manage && isResearcher && s.status === "pending" ? (
                    <button type="button" onClick={() => setReviewing(s)} className="btn btn-primary btn-sm">
                      Review
                    </button>
                  ) : undefined
                }
              />
            ))}
          </div>
        )}
      </section>

      <ReviewModal submission={reviewing} loading={busy} onClose={() => setReviewing(null)} onSubmit={review} />
    </div>
  );
}

/* ------------------------------ Student submit ------------------------------ */

function SubmitCard({
  projectId,
  completed,
  onSubmitted,
}: {
  projectId: string;
  completed: boolean;
  onSubmitted: () => Promise<void>;
}) {
  const [commit, setCommit] = useState("");
  const [desc, setDesc] = useState("");
  const [entries, setEntries] = useState<PickedFile[]>([]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [result, setResult] = useState<SubmissionOut | null>(null);
  const [blocked, setBlocked] = useState(false);

  const len = commit.trim().length;
  const valid = len >= 10 && len <= 280;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!valid || completed || saving) return;
    setSaving(true);
    setFormError(null);
    try {
      const fd = new FormData();
      fd.append("commit_msg", commit.trim());
      if (desc.trim()) fd.append("description", desc.trim());
      entries.forEach((en) => fd.append("files", en.file, en.file.name));
      fd.append("paths", JSON.stringify(entries.map((en) => en.path)));
      const res = await api.upload<SubmissionOut>(`/projects/${projectId}/submissions`, fd);
      setResult(res);
      setCommit("");
      setDesc("");
      setEntries([]);
      toast.success("Work submitted");
      await onSubmitted();
    } catch (err) {
      if (err instanceof ApiError && err.code === "BLACKLISTED") {
        setBlocked(true);
      } else if (err instanceof ApiError && err.code === "DUPLICATE_SUBMISSION") {
        setFormError("Too similar to a previous submission");
      } else if (err instanceof ApiError && err.status === 422) {
        setFormError(err.detail);
      } else {
        toast.error(errMsg(err));
      }
    } finally {
      setSaving(false);
    }
  }

  if (blocked) return <BlockedNotice />;

  return (
    <section className="card space-y-4">
      <h2 className="section-title">Submit work</h2>
      {completed && <p className="muted rounded-xl bg-slate-50 p-3">This project is completed, so new submissions are closed.</p>}

      {result && (
        <div className="space-y-3" aria-live="polite">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-slate-900">Submission received</span>
            <OriginalityBadge originality={result.originality} />
            <button type="button" onClick={() => setResult(null)} className="btn btn-ghost btn-sm">Dismiss</button>
          </div>
          {result.integrity?.action === "warned" && (
            <div role="alert" className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm font-semibold text-red-800">
              This looks copied. This is your first warning. Your researchers and sponsor were notified. A second
              incident blocks your account.
            </div>
          )}
        </div>
      )}

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="commit-msg" className="label">Commit message</label>
          <input
            id="commit-msg"
            type="text"
            value={commit}
            maxLength={280}
            disabled={completed || saving}
            aria-describedby="commit-help"
            onChange={(e) => {
              setCommit(e.target.value);
              setFormError(null);
            }}
            className="input"
          />
          <div id="commit-help" className="mt-1 flex items-start justify-between gap-3">
            <span className="help">Describe what you built, where and how, like a good git commit message</span>
            <span className={clsx("help shrink-0 tabular-nums", len > 0 && len < 10 && "!text-amber-600")}>{len}/280 (min 10)</span>
          </div>
          {formError && <p role="alert" className="error-text mt-2">{formError}</p>}
        </div>

        <div>
          <label htmlFor="commit-desc" className="label">
            Description <span className="font-normal text-slate-400">(optional)</span>
          </label>
          <textarea id="commit-desc" value={desc} rows={3} disabled={completed || saving} onChange={(e) => setDesc(e.target.value)} className="input" />
        </div>

        <div>
          <span className="label">Files</span>
          <FilePicker entries={entries} onChange={setEntries} disabled={completed || saving} />
        </div>

        <button type="submit" disabled={!valid || completed || saving} className="btn btn-primary">
          {saving && <Spinner className="h-4 w-4" />}
          Submit work
        </button>
      </form>
    </section>
  );
}
