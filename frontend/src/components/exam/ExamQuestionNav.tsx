"use client";

import { cn } from "@/lib/utils";

interface ExamQuestionNavProps {
  totalQuestions: number;
  currentIndex: number;
  answers: Record<number, string>;
  onNavigate: (index: number) => void;
}

export function ExamQuestionNav({
  totalQuestions,
  currentIndex,
  answers,
  onNavigate,
}: ExamQuestionNavProps) {
  return (
    <div className="flex flex-wrap gap-2 lg:flex-col">
      <p className="hidden text-xs font-semibold uppercase tracking-wider text-muted-foreground lg:block">
        Questions
      </p>
      {Array.from({ length: totalQuestions }, (_, i) => {
        const qNum = i + 1;
        const isAnswered = !!(answers[qNum] && answers[qNum].trim());
        const isCurrent = i === currentIndex;

        return (
          <button
            key={qNum}
            onClick={() => onNavigate(i)}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-lg text-sm font-medium transition-all",
              isCurrent
                ? "bg-primary text-primary-foreground shadow-sm ring-2 ring-primary/30"
                : isAnswered
                  ? "bg-primary/15 text-primary hover:bg-primary/25"
                  : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
            )}
            aria-label={`Question ${qNum}${isAnswered ? " (answered)" : ""}${isCurrent ? " (current)" : ""}`}
            aria-current={isCurrent ? "step" : undefined}
          >
            {qNum}
          </button>
        );
      })}
    </div>
  );
}
