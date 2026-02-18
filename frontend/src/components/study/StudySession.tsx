"use client";

import { useState, useCallback } from "react";
import { BookOpen, RefreshCw } from "lucide-react";
import { useStudy } from "@/lib/hooks/useStudy";
import { SubjectSelector } from "./SubjectSelector";
import { QuestionCard } from "./QuestionCard";
import { AnswerInput } from "./AnswerInput";
import { GradeDisplay } from "./GradeDisplay";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type SessionPhase = "select" | "question" | "answer" | "grading" | "result";

interface StudySessionProps {
  className?: string;
}

export function StudySession({ className }: StudySessionProps) {
  const [phase, setPhase] = useState<SessionPhase>("select");
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
  }, [reset]);

  const handleTryAnother = useCallback(async () => {
    reset();
    setPhase("question");
    await generateQuestion({ subject: selectedSubject, topic: selectedTopic });
    setPhase("answer");
  }, [reset, selectedSubject, selectedTopic, generateQuestion]);

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

      {/* Answer input */}
      {phase === "answer" && currentQuestion && (
        <AnswerInput
          value={answer}
          onChange={setAnswer}
          onSubmit={handleSubmitAnswer}
          isGrading={false}
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
