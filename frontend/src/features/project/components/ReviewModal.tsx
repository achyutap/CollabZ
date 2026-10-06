"use client";

import { useEffect, useState } from "react";
import { OriginalityBadge, Spinner } from "@/components/common";
import type { SubmissionOut } from "@/lib/types";

interface Props {
  submission: SubmissionOut | null;
  loading: boolean;
  onClose: () => void;
  onSubmit: (approve: boolean, feedback: string, publicFileIds: string[]) => void | Promise<void>;
}

export default function ReviewModal({ submission, loading, onClose, onSubmit }: Props) {
  const [feedback, setFeedback] = useState("");
  const [publicIds, setPublicIds] = useState<string[]>([]);
  const id = submission?.id ?? null;

  useEffect(() => {
    setFeedback("");
    setPublicIds([]);
  }, [id]);

  useEffect(() => {
    if (!id) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onClose();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [id, loading, onClose]);

  if (!submission) return null;

  function toggle(fid: string) {
    setPublicIds((cur) => (cur.includes(fid) ? cur.filter((x) => x !== fid) : [...cur, fid]));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="review-title"
        className="card max-h-[90vh] w-full max-w-lg space-y-4 overflow-y-auto shadow-xl"
      >
        <div>
          <h2 id="review-title" className="section-title">Review submission</h2>
          <p className="muted mt-1 line-clamp-2 break-words">&ldquo;{submission.commit_msg}&rdquo; by {submission.student_name}</p>
        </div>

        <div>
          <label htmlFor="review-feedback" className="label">Feedback for the student</label>
          <textarea
            id="review-feedback"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={4}
            autoFocus
            className="input"
            placeholder="What worked, what is missing, what should change?"
          />
          <p className="help mt-1">Optional, but feedback is strongly encouraged, especially when rejecting.</p>
        </div>

        {submission.files.length > 0 && (
          <fieldset>
            <legend className="label">Make public (only applies when approving)</legend>
            <p className="help mb-2">Public files can be seen by any logged-in user and show up in Explore.</p>
            <ul className="max-h-44 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
              {submission.files.map((f) => {
                const copied = f.originality === "copied";
                return (
                  <li key={f.id}>
                    <label className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm">
                      <input
                        type="checkbox"
                        checked={publicIds.includes(f.id)}
                        disabled={copied || loading}
                        onChange={() => toggle(f.id)}
                      />
                      <span className="min-w-0 flex-1 truncate font-mono text-xs">{f.path}</span>
                      {copied && <OriginalityBadge originality="copied" />}
                    </label>
                  </li>
                );
              })}
            </ul>
          </fieldset>
        )}

        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" onClick={onClose} disabled={loading} className="btn btn-secondary">
            Cancel
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => void onSubmit(false, feedback, [])}
            className="btn btn-danger"
          >
            Reject
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => void onSubmit(true, feedback, publicIds)}
            className="btn btn-primary"
          >
            {loading && <Spinner className="h-4 w-4" />}
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
