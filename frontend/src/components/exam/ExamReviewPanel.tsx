"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CheckCircle2, AlertCircle, ArrowLeft } from "lucide-react";
import type { ExamQuestion } from "@/lib/types/exam";

interface ExamReviewPanelProps {
  questions: ExamQuestion[];
  answers: Record<number, string>;
  onGoBack: () => void;
  onSubmit: () => void;
  onNavigateToQuestion: (index: number) => void;
}

export function ExamReviewPanel({
  questions,
  answers,
  onGoBack,
  onSubmit,
  onNavigateToQuestion,
}: ExamReviewPanelProps) {
  const answered = questions.filter(
    (q) => answers[q.number] && answers[q.number].trim()
  );
  const unanswered = questions.filter(
    (q) => !answers[q.number] || !answers[q.number].trim()
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold">Review Your Answers</h2>
        <p className="text-muted-foreground">
          Check your answers before submitting. You cannot change answers after
          submission.
        </p>
      </div>

      {/* Summary */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              Answered
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {answered.length}
              <span className="text-lg font-normal text-muted-foreground">
                {" "}
                / {questions.length}
              </span>
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-5 w-5 text-amber-500" />
              Unanswered
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-amber-600">
              {unanswered.length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Unanswered warning */}
      {unanswered.length > 0 && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
          <p className="mb-2 text-sm font-medium text-amber-700 dark:text-amber-400">
            The following questions are unanswered:
          </p>
          <div className="flex flex-wrap gap-2">
            {unanswered.map((q) => (
              <button
                key={q.number}
                onClick={() =>
                  onNavigateToQuestion(
                    questions.findIndex((qn) => qn.number === q.number)
                  )
                }
                className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-sm font-medium text-amber-700 transition-colors hover:bg-amber-500/20 dark:text-amber-400"
              >
                Q{q.number}
                <Badge variant="outline" className="ml-1 text-xs">
                  {q.marks}m
                </Badge>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Question list */}
      <div className="space-y-2">
        {questions.map((q, idx) => {
          const ans = answers[q.number];
          const hasAnswer = ans && ans.trim();
          return (
            <button
              key={q.number}
              onClick={() => onNavigateToQuestion(idx)}
              className="flex w-full items-center justify-between rounded-lg border p-3 text-left transition-colors hover:bg-accent"
            >
              <div className="flex items-center gap-3">
                {hasAnswer ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-amber-500" />
                )}
                <span className="text-sm font-medium">
                  Question {q.number}
                </span>
                <Badge variant="outline" className="text-xs">
                  {q.marks} marks
                </Badge>
              </div>
              <span className="text-xs text-muted-foreground">
                {hasAnswer
                  ? `${ans.trim().split(/\s+/).length} words`
                  : "No answer"}
              </span>
            </button>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="outline" onClick={onGoBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Go Back
        </Button>
        <Button onClick={onSubmit}>Submit Exam</Button>
      </div>
    </div>
  );
}
