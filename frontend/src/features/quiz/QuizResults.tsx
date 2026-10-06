"use client";

import Link from "next/link";
import type { QuizSubmitResult } from "@/lib/types";
import { PageHeader, SkillChip, Spinner, StarRating, skillLabel } from "@/components/common";

const PASS_PCT = 60;

interface Props {
  result: QuizSubmitResult;
  retaking: boolean;
  onRetake: (skills: string[]) => void;
}

export default function QuizResults({ result, retaking, onRetake }: Props) {
  const failed = result.per_skill.filter((s) => !s.passed).map((s) => s.skill);
  return (
    <div className="page">
      <PageHeader title="Quiz results" description={`You answered ${result.total_correct} of ${result.total} correctly.`} />

      <section className="card">
        <h2 className="section-title mb-4">Score by skill</h2>
        <ul className="space-y-4">
          {result.per_skill.map((s) => {
            const pct = s.total > 0 ? Math.round((s.correct / s.total) * 100) : 0;
            return (
              <li key={s.skill}>
                <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="font-medium text-slate-800">{skillLabel(s.skill)}</span>
                  <span className="flex items-center gap-3">
                    <span className={s.passed ? "text-emerald-600" : "text-red-600"}>
                      {s.correct}/{s.total} · {pct}% · {s.passed ? "Verified" : "Not passed"}
                    </span>
                    {!s.passed && (
                      <button type="button" disabled={retaking} onClick={() => onRetake([s.skill])} className="btn btn-secondary btn-sm">
                        Retake
                      </button>
                    )}
                  </span>
                </div>
                <div className="relative h-3 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label={`${skillLabel(s.skill)} score`}>
                  <div className={`h-full rounded-full ${s.passed ? "bg-emerald-500" : "bg-red-400"}`} style={{ width: `${pct}%` }} />
                  <div className="absolute inset-y-0 w-px bg-slate-500" style={{ left: `${PASS_PCT}%` }} aria-hidden />
                </div>
              </li>
            );
          })}
        </ul>
        <p className="help">Pass mark: {PASS_PCT}%</p>
      </section>

      <section className="card">
        <h2 className="section-title mb-3">Skills added to your profile</h2>
        {result.added_skills.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {result.added_skills.map((s) => (
              <SkillChip key={s} label={skillLabel(s)} variant="matched" />
            ))}
          </div>
        ) : (
          <p className="muted">No skills were verified this time. You can retake the quiz for any skill you didn&apos;t pass.</p>
        )}
      </section>

      {result.temp_rating !== null && (
        <section className="card flex flex-col items-center text-center">
          <h2 className="section-title mb-3">Your rating</h2>
          <div className="origin-center scale-150 py-3">
            <StarRating value={result.temp_rating} size="md" showValue />
          </div>
          <p className="muted mt-4">Based on your quiz</p>
        </section>
      )}

      <div className="flex flex-wrap gap-2">
        {failed.length > 1 && (
          <button type="button" disabled={retaking} onClick={() => onRetake(failed)} className="btn btn-secondary">
            {retaking && <Spinner className="h-4 w-4" />}
            Retake failed skills
          </button>
        )}
        <Link href="/profile" className="btn btn-primary">
          Go to profile
        </Link>
      </div>
    </div>
  );
}
