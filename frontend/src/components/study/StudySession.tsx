"use client";

import { useState, useCallback } from "react";
import { BookOpen, RefreshCw, Lightbulb, Eye, EyeOff, Loader2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useStudy } from "@/lib/hooks/useStudy";
import { api } from "@/lib/api-client";
import { SubjectSelector } from "./SubjectSelector";
import { QuestionCard } from "./QuestionCard";
import { AnswerInput } from "./AnswerInput";
import { GradeDisplay } from "./GradeDisplay";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type SessionPhase = "select" | "question" | "answer" | "grading" | "result";

interface StudySessionProps {
  className?: string;
}

export function StudySession({ className }: StudySessionProps) {
  const [phase, setPhase] = useState<SessionPhase>("select");
  const [hints, setHints] = useState<string[]>([]);
  const [hintLevel, setHintLevel] = useState(0);
  const [showModelAnswer, setShowModelAnswer] = useState(false);
  const [attachments, setAttachments] = useState<File[]>([]);

  const {
    currentQuestion,
    answer,
    gradeResult,
    isGenerating,
    isGrading,
    streamedContent,
    selectedSubject,
    selectedTopic,
    setAnswer,
    setSelectedSubject,
    setSelectedTopic,
    generateQuestion,
    gradeAnswer,
    reset,
  } = useStudy();

  // Hint mutation
  const hintMutation = useMutation({
    mutationFn: async (level: number) => {
      return api.post<{ hint: string; hint_level: number }>("/api/study/hint", {
        question: currentQuestion?.question_text ?? currentQuestion?.question ?? "",
        command_term: currentQuestion?.command_term ?? "",
        hint_level: level,
      });
    },
    onSuccess: (data) => {
      setHints((prev) => [...prev, data.hint]);
      setHintLevel(data.hint_level);
    },
  });

  const handleSelect = useCallback(
    (subject: string, topic: string) => {
      setSelectedSubject(subject);
      if (topic) {
        setSelectedTopic(topic);
      }
    },
    [setSelectedSubject, setSelectedTopic]
  );

  const handleGenerate = useCallback(async () => {
    if (!selectedSubject || !selectedTopic) return;
    setPhase("question");
    setHints([]);
    setHintLevel(0);
    setShowModelAnswer(false);
    setAttachments([]);
    await generateQuestion({ subject: selectedSubject, topic: selectedTopic });
    setPhase("answer");
  }, [selectedSubject, selectedTopic, generateQuestion]);

  const handleSubmitAnswer = useCallback(async () => {
    if (!currentQuestion || !answer.trim()) return;
    setPhase("grading");
    await gradeAnswer({ question: currentQuestion, answer });
    setPhase("result");
  }, [currentQuestion, answer, gradeAnswer]);

  const handleNextQuestion = useCallback(() => {
    reset();
    setPhase("select");
    setHints([]);
    setHintLevel(0);
    setShowModelAnswer(false);
    setAttachments([]);
  }, [reset]);

  const handleTryAnother = useCallback(async () => {
    reset();
    setHints([]);
    setHintLevel(0);
    setShowModelAnswer(false);
    setAttachments([]);
    setPhase("question");
    await generateQuestion({ subject: selectedSubject, topic: selectedTopic });
    setPhase("answer");
  }, [reset, selectedSubject, selectedTopic, generateQuestion]);

  const handleGetHint = useCallback(() => {
    const nextLevel = Math.min(hintLevel + 1, 3);
    hintMutation.mutate(nextLevel);
  }, [hintLevel, hintMutation]);

  return (
    <div className={cn("mx-auto max-w-3xl space-y-6", className)}>
      {/* Subject & topic selection */}
      {phase === "select" && (
        <div className="space-y-6">
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <BookOpen className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-semibold">Start a Study Session</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Choose a subject and topic to generate a practice question
            </p>
          </div>
          <SubjectSelector
            selectedSubject={selectedSubject}
            selectedTopic={selectedTopic}
            onSelect={handleSelect}
          />
          <div className="flex justify-center">
            <Button
              onClick={handleGenerate}
              disabled={!selectedSubject || !selectedTopic}
              size="lg"
            >
              <BookOpen className="mr-2 h-4 w-4" />
              Generate Question
            </Button>
          </div>
        </div>
      )}

      {/* Loading skeleton while generating */}
      {phase === "question" && isGenerating && !currentQuestion && (
        <Card>
          <CardContent className="space-y-4 pt-6">
            <div className="flex gap-2">
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-12" />
            </div>
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </CardContent>
        </Card>
      )}

      {/* Question card - show once we have a question, even while still streaming */}
      {currentQuestion && (phase === "question" || phase === "answer") && (
        <QuestionCard
          question={currentQuestion}
          streamedContent={isGenerating ? streamedContent : undefined}
        />
      )}

      {/* Hints & Model Answer toolbar (during answer phase) */}
      {phase === "answer" && currentQuestion && (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleGetHint}
            disabled={hintMutation.isPending || hintLevel >= 3}
          >
            {hintMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Lightbulb className="mr-2 h-4 w-4" />
            )}
            {hintLevel === 0
              ? "Get Hint"
              : hintLevel >= 3
                ? "Max Hints Used"
                : `Get More Hints (${hintLevel}/3)`}
          </Button>

          {currentQuestion.model_answer && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowModelAnswer(!showModelAnswer)}
            >
              {showModelAnswer ? (
                <EyeOff className="mr-2 h-4 w-4" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              {showModelAnswer ? "Hide Model Answer" : "View Model Answer"}
            </Button>
          )}
        </div>
      )}

      {/* Hints display */}
      {hints.length > 0 && (phase === "answer" || phase === "grading") && (
        <Card className="border-amber-200 bg-amber-50/50 dark:border-amber-700 dark:bg-amber-900/10">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Lightbulb className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <span className="text-amber-800 dark:text-amber-300">
                Hints ({hints.length}/3)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {hints.map((hint, i) => (
              <div
                key={i}
                className="rounded-md bg-amber-100/50 p-2.5 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-200"
              >
                <span className="mr-1.5 font-semibold">Hint {i + 1}:</span>
                {hint}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Model answer reveal */}
      {showModelAnswer && currentQuestion?.model_answer && phase === "answer" && (
        <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-700 dark:bg-blue-900/10">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-blue-800 dark:text-blue-300">
              Model Answer
            </CardTitle>
          </CardHeader>
          <CardContent>
            <MarkdownRenderer content={currentQuestion.model_answer} />
          </CardContent>
        </Card>
      )}

      {/* Answer input */}
      {phase === "answer" && currentQuestion && (
        <AnswerInput
          value={answer}
          onChange={setAnswer}
          onSubmit={handleSubmitAnswer}
          isGrading={false}
          attachments={attachments}
          onAttachmentsChange={setAttachments}
        />
      )}

      {/* Grading in progress */}
      {phase === "grading" && (
        <>
          {currentQuestion && <QuestionCard question={currentQuestion} />}
          <AnswerInput
            value={answer}
            onChange={setAnswer}
            onSubmit={handleSubmitAnswer}
            isGrading={true}
          />
        </>
      )}

      {/* Grade result */}
      {phase === "result" && gradeResult && (
        <>
          {currentQuestion && <QuestionCard question={currentQuestion} />}
          <GradeDisplay result={gradeResult} />
          <div className="flex justify-center gap-3">
            <Button variant="outline" onClick={handleNextQuestion}>
              <RefreshCw className="mr-2 h-4 w-4" />
              New Topic
            </Button>
            <Button onClick={handleTryAnother}>
              <BookOpen className="mr-2 h-4 w-4" />
              Another Question
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
