"use client";

import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ExamQuestion } from "@/lib/types/exam";

interface ExamQuestionPanelProps {
  question: ExamQuestion;
  questionIndex: number;
  totalQuestions: number;
  answer: string;
  onAnswerChange: (answer: string) => void;
  onPrev: () => void;
  onNext: () => void;
  readOnly?: boolean;
}

export function ExamQuestionPanel({
  question,
  questionIndex,
  totalQuestions,
  answer,
  onAnswerChange,
  onPrev,
  onNext,
  readOnly = false,
}: ExamQuestionPanelProps) {
  return (
    <div className="space-y-4">
      {/* Question header */}
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-lg font-semibold">
          Question {question.number}
        </h3>
        <div className="flex items-center gap-2">
          {question.command_term && (
            <Badge variant="outline">{question.command_term}</Badge>
          )}
          <Badge variant="secondary">{question.marks} marks</Badge>
        </div>
      </div>

      {/* Question text */}
      <div className="rounded-lg border bg-muted/30 p-4">
        <MarkdownRenderer content={question.question_text} />
      </div>

      {/* Answer area */}
      {!readOnly && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Your Answer
          </label>
          <Textarea
            value={answer}
            onChange={(e) => onAnswerChange(e.target.value)}
            placeholder="Type your answer here..."
            className="min-h-[200px] resize-y"
          />
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onPrev}
          disabled={questionIndex === 0}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Previous
        </Button>
        <span className="text-sm text-muted-foreground">
          {questionIndex + 1} of {totalQuestions}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={onNext}
          disabled={questionIndex === totalQuestions - 1}
        >
          Next
          <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
