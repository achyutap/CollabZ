"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Timer } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { toast } from "@/lib/toast";
import type { QuizQuestion, QuizStartOut, QuizSubmitResult } from "@/lib/types";
import SkillPicker from "./SkillPicker";
import QuestionView from "./QuestionView";
import ReviewScreen from "./ReviewScreen";
import QuizResults from "./QuizResults";

type Phase = "pick" | "taking" | "review" | "results";
const DURATION_MS = 30 * 60 * 1000;

function formatTime(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function QuizFlow() {
  const { refreshUser } = useAuth();
  const [phase, setPhase] = useState<Phase>("pick");
  const [attemptToken, setAttemptToken] = useState("");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [index, setIndex] = useState(0);
  const [deadline, setDeadline] = useState(0);
  const [remainingMs, setRemainingMs] = useState(DURATION_MS);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<QuizSubmitResult | null>(null);
  const submittingRef = useRef(false);

  const reset = useCallback(() => {
    setPhase("pick");
    setAttemptToken("");
    setQuestions([]);
    setAnswers({});
    setIndex(0);
    setResult(null);
  }, []);

  const start = async (skills: string[]) => {
    setStarting(true);
    try {
      const res = await api.post<QuizStartOut>("/quiz/start", { skills });
      setAttemptToken(res.attempt_token);
      setQuestions(res.questions);
      setAnswers({});
      setIndex(0);
      setDeadline(Date.now() + DURATION_MS);
      setRemainingMs(DURATION_MS);
      setPhase("taking");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.detail : "Could not start the quiz");
    } finally {
      setStarting(false);
    }
  };

  const submit = useCallback(
    async (auto: boolean): Promise<void> => {
      if (submittingRef.current) return;
      submittingRef.current = true;
      setSubmitting(true);
      try {
        const res = await api.post<QuizSubmitResult>("/quiz/submit", {
          attempt_token: attemptToken,
          answers: questions
            .filter((q) => answers[q.id] !== undefined)
            .map((q) => ({ question_id: q.id, selected_index: answers[q.id] })),
        });
        setResult(res);
        setPhase("results");
        if (auto) toast.success("Time is up — your answers were submitted automatically.");
        void refreshUser();
      } catch (e) {
        if (e instanceof ApiError && e.code === "INVALID_TOKEN") {
          toast.error("This quiz attempt is no longer valid. Please start again.");
          reset();
        } else {
          toast.error(e instanceof ApiError ? e.detail : "Could not submit the quiz");
        }
      } finally {
        submittingRef.current = false;
        setSubmitting(false);
      }
    },
    [attemptToken, questions, answers, refreshUser, reset],
  );

  const submitRef = useRef(submit);
  useEffect(() => {
    submitRef.current = submit;
  }, [submit]);

  useEffect(() => {
    if (phase !== "taking" && phase !== "review") return;
    const tick = () => {
      const rem = deadline - Date.now();
      setRemainingMs(Math.max(0, rem));
      if (rem <= 0) {
        clearInterval(timer);
        void submitRef.current(true);
      }
    };
    const timer = setInterval(tick, 1000);
    tick();
    return () => clearInterval(timer);
  }, [phase, deadline]);

  const timerBar = (
    <div className={`flex items-center justify-end gap-2 text-sm font-medium ${remainingMs < 5 * 60 * 1000 ? "text-red-600" : "text-slate-600"}`} role="timer" aria-label="Time remaining">
      <Timer className="h-4 w-4" aria-hidden />
      {formatTime(remainingMs)} left
      {submitting && <span className="text-slate-400">Submitting…</span>}
    </div>
  );

  if (phase === "pick") return <SkillPicker starting={starting} onStart={start} />;

  if (phase === "results" && result) return <QuizResults result={result} retaking={starting} onRetake={(skills) => void start(skills)} />;

  if (phase === "review") {
    return (
      <div className="page">
        {timerBar}
        <ReviewScreen
          questions={questions}
          answers={answers}
          submitting={submitting}
          onJump={(i) => {
            setIndex(i);
            setPhase("taking");
          }}
          onBack={() => setPhase("taking")}
          onSubmit={() => submit(false)}
        />
      </div>
    );
  }

  const q = questions[index];
  if (!q) return null;
  return (
    <div className="page">
      {timerBar}
      <QuestionView
        question={q}
        index={index}
        total={questions.length}
        selected={answers[q.id]}
        onSelect={(i) => setAnswers((a) => ({ ...a, [q.id]: i }))}
        onPrev={() => setIndex((i) => Math.max(0, i - 1))}
        onNext={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}
        onReview={() => setPhase("review")}
      />
    </div>
  );
}
