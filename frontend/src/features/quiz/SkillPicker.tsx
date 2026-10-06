"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ClipboardCheck, Clock } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { QuizSkill } from "@/lib/types";
import { EmptyState, PageHeader, SkillChip, Spinner } from "@/components/common";

const MAX_SKILLS = 5;

interface Props {
  starting: boolean;
  onStart: (skills: string[]) => void;
}

export default function SkillPicker({ starting, onStart }: Props) {
  const { data, error, loading, refetch } = useFetch<QuizSkill[]>("/quiz/skills");
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    if (error) toast.error(error.detail);
  }, [error]);

  const toggle = (id: string) => {
    setSelected((s) => {
      if (s.includes(id)) return s.filter((x) => x !== id);
      if (s.length >= MAX_SKILLS) {
        toast.error(`You can pick at most ${MAX_SKILLS} skills`);
        return s;
      }
      return [...s, id];
    });
  };

  return (
    <div className="page">
      <PageHeader title="Verify your skills" description="Pass a short quiz for each skill to verify it on your profile." />
      {loading && !data ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : error && !data ? (
        <EmptyState
          title="Could not load your skills"
          description={error.detail}
          action={
            <button type="button" onClick={() => void refetch()} className="btn btn-primary">
              Retry
            </button>
          }
        />
      ) : !data || data.length === 0 ? (
        <EmptyState
          icon={<ClipboardCheck className="h-6 w-6" aria-hidden />}
          title="Nothing to verify"
          description="Add skills from your profile to take a quiz."
          action={
            <Link href="/profile" className="btn btn-primary">
              Go to profile
            </Link>
          }
        />
      ) : (
        <div className="card space-y-5">
          <fieldset>
            <legend className="section-title">Choose 1 to {MAX_SKILLS} skills to verify</legend>
            <div className="mt-3 flex flex-wrap gap-2">
              {data.map((s) => (
                <SkillChip key={s.id} label={s.label} variant={selected.includes(s.id) ? "selected" : "default"} onClick={() => toggle(s.id)} />
              ))}
            </div>
            <p className="help">{selected.length} of {MAX_SKILLS} selected</p>
          </fieldset>
          <p className="flex items-center gap-2 text-sm text-slate-500">
            <Clock className="h-4 w-4" aria-hidden /> You will have 30 minutes. The quiz submits automatically when time runs out.
          </p>
          <button type="button" disabled={selected.length === 0 || starting} onClick={() => onStart(selected)} className="btn btn-primary">
            {starting && <Spinner className="h-4 w-4 text-white" />}
            Start quiz
          </button>
        </div>
      )}
    </div>
  );
}
