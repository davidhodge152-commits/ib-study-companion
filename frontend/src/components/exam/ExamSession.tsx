"use client";

import { useCallback, useEffect, useRef } from "react";
import { useExamStore } from "@/lib/stores/exam-store";
import { useExamGenerate, useExamSubmit, useExamResults } from "@/lib/hooks/useExam";
import { ExamConfig } from "./ExamConfig";
import { ExamReadingTime } from "./ExamReadingTime";
import { ExamTimer } from "./ExamTimer";
import { ExamQuestionNav } from "./ExamQuestionNav";
import { ExamQuestionPanel } from "./ExamQuestionPanel";
import { ExamReviewPanel } from "./ExamReviewPanel";
import { ExamResults } from "./ExamResults";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useState } from "react";
import { ClipboardCheck } from "lucide-react";

export function ExamSession() {
  const store = useExamStore();
  const generateExam = useExamGenerate();
  const submitExam = useExamSubmit();
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [submittedGrade, setSubmittedGrade] = useState<number | null>(null);
  const hasExpiredRef = useRef(false);

  const {
    sessionId,
    paper,
    phase,
    answers,
    currentQuestionIndex,
    examStartTime,
    readingStartTime,
  } = store;

  // Tab title during active exam
  useEffect(() => {
    if (phase !== "active" || !examStartTime || !paper) return;

    const originalTitle = document.title;
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - examStartTime) / 1000);
      const remaining = Math.max(0, paper.duration_minutes * 60 - elapsed);
      const m = Math.floor(remaining / 60);
      const s = remaining % 60;
      document.title = `(${m}:${String(s).padStart(2, "0")}) Exam — IB Study`;
    }, 1000);

    return () => {
      clearInterval(interval);
      document.title = originalTitle;
    };
  }, [phase, examStartTime, paper]);

  // beforeunload warning during active/reading phase
  useEffect(() => {
    if (phase !== "active" && phase !== "reading") return;

    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };

    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [phase]);

  const handleStart = useCallback(
    async (subject: string, level: string, paperNumber: number) => {
      const result = await generateExam.mutateAsync({
        subject,
        level,
        paper_number: paperNumber,
      });
      store.setPaper(result.session_id, {
        ...result.paper,
        subject,
        level,
        paper_number: paperNumber,
      });
      store.startReading();
    },
    [generateExam, store]
  );

  const handleSkipReading = useCallback(() => {
    store.startExam();
  }, [store]);

  const handleReadingExpired = useCallback(() => {
    store.startExam();
  }, [store]);

  const handleTimerExpired = useCallback(() => {
    if (hasExpiredRef.current) return;
    hasExpiredRef.current = true;
    setShowSubmitDialog(true);
  }, []);

  const handleGoToReview = useCallback(() => {
    store.setPhase("review");
  }, [store]);

  const handleGoBackToExam = useCallback(() => {
    store.setPhase("active");
  }, [store]);

  const handleNavigateToQuestion = useCallback(
    (index: number) => {
      store.setCurrentQuestionIndex(index);
      if (phase === "review") {
        store.setPhase("active");
      }
    },
    [store, phase]
  );

  const handleSubmit = useCallback(async () => {
    if (!sessionId || !paper) return;

    store.setPhase("submitting");
    setShowSubmitDialog(false);

    const answerList = paper.questions.map((q) => ({
      question_number: q.number,
      answer: answers[q.number] || "",
    }));

    const totalMarks = paper.total_marks;
    // Estimated earned marks (server will calculate actual grade)
    const earnedMarks = Math.round(
      totalMarks *
        (answerList.filter((a) => a.answer.trim()).length /
          (paper.questions.length || 1))
    );

    const result = await submitExam.mutateAsync({
      sessionId,
      answers: answerList,
      earned_marks: earnedMarks,
      total_marks: totalMarks,
      subject: paper.subject,
      level: paper.level,
    });

    setSubmittedGrade(result.grade);
    store.setPhase("results");
  }, [sessionId, paper, answers, submitExam, store]);

  const handleNewExam = useCallback(() => {
    hasExpiredRef.current = false;
    setSubmittedGrade(null);
    store.reset();
  }, [store]);

  // Phase: config
  if (phase === "config") {
    return (
      <ExamConfig
        onStart={handleStart}
        isGenerating={generateExam.isPending}
      />
    );
  }

  // Need paper for all other phases
  if (!paper) {
    store.reset();
    return null;
  }

  // Phase: reading
  if (phase === "reading" && readingStartTime) {
    return (
      <ExamReadingTime
        paper={paper}
        readingStartTime={readingStartTime}
        onSkip={handleSkipReading}
        onExpired={handleReadingExpired}
      />
    );
  }

  // Phase: active
  if (phase === "active" && examStartTime) {
    const currentQ = paper.questions[currentQuestionIndex];
    if (!currentQ) return null;

    return (
      <div className="space-y-4">
        <ExamTimer
          startTime={examStartTime}
          durationMinutes={paper.duration_minutes}
          onExpired={handleTimerExpired}
        />

        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Question nav sidebar */}
          <div className="shrink-0 lg:w-16">
            <ExamQuestionNav
              totalQuestions={paper.questions.length}
              currentIndex={currentQuestionIndex}
              answers={answers}
              onNavigate={handleNavigateToQuestion}
            />
          </div>

          {/* Question panel */}
          <div className="flex-1">
            <ExamQuestionPanel
              question={currentQ}
              questionIndex={currentQuestionIndex}
              totalQuestions={paper.questions.length}
              answer={answers[currentQ.number] || ""}
              onAnswerChange={(a) => store.setAnswer(currentQ.number, a)}
              onPrev={() =>
                store.setCurrentQuestionIndex(
                  Math.max(0, currentQuestionIndex - 1)
                )
              }
              onNext={() =>
                store.setCurrentQuestionIndex(
                  Math.min(
                    paper.questions.length - 1,
                    currentQuestionIndex + 1
                  )
                )
              }
            />
          </div>
        </div>

        {/* Review button */}
        <div className="flex justify-end pt-4">
          <Button onClick={handleGoToReview}>
            <ClipboardCheck className="mr-2 h-4 w-4" />
            Review & Submit
          </Button>
        </div>

        {/* Auto-submit dialog */}
        <AlertDialog
          open={showSubmitDialog}
          onOpenChange={setShowSubmitDialog}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Time&apos;s Up!</AlertDialogTitle>
              <AlertDialogDescription>
                Your exam time has expired. Your answers will be submitted now.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogAction onClick={handleSubmit}>
                Submit Exam
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    );
  }

  // Phase: review
  if (phase === "review") {
    return (
      <ExamReviewPanel
        questions={paper.questions}
        answers={answers}
        onGoBack={handleGoBackToExam}
        onSubmit={handleSubmit}
        onNavigateToQuestion={handleNavigateToQuestion}
      />
    );
  }

  // Phase: submitting
  if (phase === "submitting") {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12">
        <LoadingSkeleton variant="card" count={1} />
        <p className="text-muted-foreground">Submitting your exam...</p>
      </div>
    );
  }

  // Phase: results
  if (phase === "results" && submittedGrade !== null) {
    return (
      <ExamResults
        grade={submittedGrade}
        earnedMarks={Math.round(
          paper.total_marks *
            (Object.values(answers).filter((a) => a.trim()).length /
              (paper.questions.length || 1))
        )}
        totalMarks={paper.total_marks}
        questions={paper.questions}
        answers={answers}
        subject={paper.subject}
        level={paper.level}
        onNewExam={handleNewExam}
      />
    );
  }

  // Fallback — reset to config
  return (
    <ExamConfig
      onStart={handleStart}
      isGenerating={generateExam.isPending}
    />
  );
}
