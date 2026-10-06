"use client";

import type { QuizQuestion } from "@/lib/types";
import { SkillChip, skillLabel } from "@/components/common";

interface Props {
  question: QuizQuestion;
  index: number;
  total: number;
  selected: number | undefined;
  onSelect: (optionIndex: number) => void;
  onPrev: () => void;
  onNext: () => void;
  onReview: () => void;
}

export default function QuestionView({ question, index, total, selected, onSelect, onPrev, onNext, onReview }: Props) {
  const isLast = index === total - 1;
  const pct = ((index + 1) / total) * 100;
  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-slate-600">
          Question {index + 1} of {total}
        </span>
        <SkillChip label={skillLabel(question.skill)} />
      </div>
      <div className="mb-6 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={index + 1} aria-label="Quiz progress">
        <div className="h-full rounded-full bg-indigo-600 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <fieldset>
        <legend className="text-base font-semibold text-slate-900">{question.question}</legend>
        <div className="mt-4 space-y-2">
          {question.options.map((opt, i) => {
            const id = `q-${question.id}-${i}`;
            const checked = selected === i;
            return (
              <label key={id} htmlFor={id} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 text-sm transition ${checked ? "border-indigo-500 bg-indigo-50" : "border-slate-200 hover:bg-slate-50"}`}>
                <input id={id} type="radio" name={`q-${question.id}`} checked={checked} onChange={() => onSelect(i)} className="mt-0.5 h-4 w-4 accent-indigo-600" />
                <span className="text-slate-800">{opt}</span>
              </label>
            );
          })}
        </div>
      </fieldset>
      <div className="mt-6 flex items-center justify-between gap-2">
        <button type="button" onClick={onPrev} disabled={index === 0} className="btn btn-secondary">
          Previous
        </button>
        <div className="flex gap-2">
          <button type="button" onClick={onReview} className="btn btn-secondary">
            Review
          </button>
          {!isLast && (
            <button type="button" onClick={onNext} className="btn btn-primary">
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
