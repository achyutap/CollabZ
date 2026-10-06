"use client";

import { useState } from "react";
import type { QuizQuestion } from "@/lib/types";
import { ConfirmDialog, skillLabel } from "@/components/common";

interface Props {
  questions: QuizQuestion[];
  answers: Record<string, number>;
  submitting: boolean;
  onJump: (index: number) => void;
  onBack: () => void;
  onSubmit: () => Promise<void>;
}

export default function ReviewScreen({ questions, answers, submitting, onJump, onBack, onSubmit }: Props) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const unanswered = questions.map((q, i) => ({ q, i })).filter(({ q }) => answers[q.id] === undefined);
  const answeredCount = questions.length - unanswered.length;

  return (
    <div className="card space-y-4">
      <h2 className="section-title">Review your answers</h2>
      <p className="muted">
        {answeredCount} of {questions.length} answered.
      </p>
      {unanswered.length > 0 ? (
        <div>
          <h3 className="mb-2 text-sm font-medium text-amber-700">Unanswered questions</h3>
          <ul className="space-y-1">
            {unanswered.map(({ q, i }) => (
              <li key={q.id}>
                <button type="button" onClick={() => onJump(i)} className="w-full rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-900 hover:bg-amber-100">
                  <span className="font-medium">Question {i + 1}</span> · {skillLabel(q.skill)}: <span className="line-clamp-1">{q.question}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">All questions answered.</p>
      )}
      <div className="flex flex-wrap justify-between gap-2 pt-2">
        <button type="button" onClick={onBack} className="btn btn-secondary">
          Back to questions
        </button>
        <button type="button" onClick={() => setConfirmOpen(true)} disabled={submitting} className="btn btn-primary">
          Submit quiz
        </button>
      </div>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Submit quiz?"
        description={
          unanswered.length > 0
            ? `You have ${unanswered.length} unanswered question${unanswered.length === 1 ? "" : "s"}. They will be marked incorrect. You cannot change answers after submitting.`
            : "You cannot change your answers after submitting."
        }
        confirmLabel="Submit"
        loading={submitting}
        onConfirm={onSubmit}
      />
    </div>
  );
}
