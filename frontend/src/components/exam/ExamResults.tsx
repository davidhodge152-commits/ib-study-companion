"use client";

import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { RotateCcw } from "lucide-react";
import type { ExamQuestion } from "@/lib/types/exam";

interface ExamResultsProps {
  grade: number;
  earnedMarks: number;
  totalMarks: number;
  questions: ExamQuestion[];
  answers: Record<number, string>;
  subject: string;
  level: string;
  onNewExam: () => void;
}

const gradeColors: Record<number, string> = {
  7: "text-green-600 bg-green-500/10 border-green-500/20",
  6: "text-green-600 bg-green-500/10 border-green-500/20",
  5: "text-blue-600 bg-blue-500/10 border-blue-500/20",
  4: "text-amber-600 bg-amber-500/10 border-amber-500/20",
  3: "text-orange-600 bg-orange-500/10 border-orange-500/20",
  2: "text-red-600 bg-red-500/10 border-red-500/20",
  1: "text-red-700 bg-red-500/10 border-red-500/20",
};

export function ExamResults({
  grade,
  earnedMarks,
  totalMarks,
  questions,
  answers,
  subject,
  level,
  onNewExam,
}: ExamResultsProps) {
  const pct = totalMarks > 0 ? Math.round((earnedMarks / totalMarks) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Grade hero */}
      <Card className={cn("text-center", gradeColors[grade] ?? gradeColors[4])}>
        <CardContent className="py-8">
          <p className="text-sm font-medium uppercase tracking-wider opacity-70">
            {subject} {level} — Final Grade
          </p>
          <p className="mt-2 text-7xl font-bold">{grade}</p>
          <p className="mt-2 text-lg">
            {earnedMarks} / {totalMarks} marks ({pct}%)
          </p>
        </CardContent>
      </Card>

      {/* Per-question breakdown */}
      <div>
        <h3 className="mb-4 text-lg font-semibold">Question Breakdown</h3>
        <div className="space-y-4">
          {questions.map((q) => {
            const ans = answers[q.number];
            const hasAnswer = ans && ans.trim();
            return (
              <Card key={q.number}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">
                      Question {q.number}
                    </CardTitle>
                    <Badge variant="secondary">{q.marks} marks</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="rounded-lg bg-muted/30 p-3">
                    <MarkdownRenderer content={q.question_text} />
                  </div>
                  <div>
                    <p className="mb-1 text-sm font-medium text-muted-foreground">
                      Your Answer
                    </p>
                    <p className="text-sm">
                      {hasAnswer ? ans : (
                        <span className="italic text-muted-foreground">
                          No answer provided
                        </span>
                      )}
                    </p>
                  </div>
                  {q.model_answer && (
                    <div>
                      <p className="mb-1 text-sm font-medium text-green-600 dark:text-green-400">
                        Model Answer
                      </p>
                      <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-3">
                        <MarkdownRenderer content={q.model_answer} />
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* New exam button */}
      <div className="text-center">
        <Button size="lg" onClick={onNewExam}>
          <RotateCcw className="mr-2 h-4 w-4" />
          Start New Exam
        </Button>
      </div>
    </div>
  );
}
