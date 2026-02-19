"use client";

import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExamTimer } from "./ExamTimer";
import type { ExamPaper } from "@/lib/types/exam";
import { Eye } from "lucide-react";

interface ExamReadingTimeProps {
  paper: ExamPaper;
  readingStartTime: number;
  onSkip: () => void;
  onExpired: () => void;
}

export function ExamReadingTime({
  paper,
  readingStartTime,
  onSkip,
  onExpired,
}: ExamReadingTimeProps) {
  const readingMinutes = paper.reading_time_minutes || 5;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Eye className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-bold">Reading Time</h2>
        </div>
        <Button variant="outline" size="sm" onClick={onSkip}>
          Skip to Exam
        </Button>
      </div>

      <ExamTimer
        startTime={readingStartTime}
        durationMinutes={readingMinutes}
        onExpired={onExpired}
      />

      <p className="text-sm text-muted-foreground">
        Read through all questions. You may not write answers during reading
        time.
      </p>

      <div className="space-y-6">
        {paper.questions.map((q) => (
          <div key={q.number} className="rounded-lg border p-4">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-semibold">Question {q.number}</h3>
              <div className="flex items-center gap-2">
                {q.command_term && (
                  <Badge variant="outline">{q.command_term}</Badge>
                )}
                <Badge variant="secondary">{q.marks} marks</Badge>
              </div>
            </div>
            <MarkdownRenderer content={q.question_text} />
          </div>
        ))}
      </div>
    </div>
  );
}
