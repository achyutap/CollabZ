"use client";

import { RoleGuard } from "@/lib/auth";
import QuizFlow from "@/features/quiz/QuizFlow";

export default function StudentQuizPage() {
  return (
    <RoleGuard roles={["student"]}>
      <QuizFlow />
    </RoleGuard>
  );
}
