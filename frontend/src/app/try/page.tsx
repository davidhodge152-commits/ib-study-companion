"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const sampleQuestions = [
  {
    id: 1,
    subject: "Mathematics AA",
    question:
      "Find the derivative of f(x) = 3x^2 + 2x - 5 and evaluate it at x = 2.",
    marks: 4,
  },
  {
    id: 2,
    subject: "Biology",
    question:
      "Explain two differences between aerobic and anaerobic respiration.",
    marks: 4,
  },
  {
    id: 3,
    subject: "English A",
    question:
      'Analyse the use of imagery in the following extract and discuss its effect on the reader.',
    marks: 6,
  },
];

export default function TryPage() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const questionsRemaining = sampleQuestions.length - currentIndex;

  const currentQuestion = sampleQuestions[currentIndex];

  function handleSubmit() {
    if (!answer.trim()) return;
    setSubmitted(true);
  }

  function handleNext() {
    if (currentIndex < sampleQuestions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      setAnswer("");
      setSubmitted(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Guest Banner */}
      <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
        <div className="flex flex-col items-start justify-between gap-2 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-medium">
              Guest Mode - {questionsRemaining}{" "}
              {questionsRemaining === 1 ? "question" : "questions"} remaining
            </p>
            <p className="text-xs text-muted-foreground">
              Sign up for unlimited access to all features
            </p>
          </div>
          <Button asChild size="sm">
            <Link href="/register">Create Free Account</Link>
          </Button>
        </div>
      </div>

      <div>
        <h1 className="text-2xl font-bold">Try IB Study Companion</h1>
        <p className="text-muted-foreground">
          Experience AI-powered IB study with sample questions
        </p>
      </div>

      {currentIndex < sampleQuestions.length ? (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">
                  Question {currentIndex + 1} of {sampleQuestions.length}
                </CardTitle>
                <CardDescription>
                  {currentQuestion.subject} -- {currentQuestion.marks} marks
                </CardDescription>
              </div>
              <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
                {currentQuestion.subject}
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed">
              {currentQuestion.question}
            </p>

            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              disabled={submitted}
              placeholder="Type your answer here..."
              rows={6}
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
            />

            {submitted && (
              <div className="rounded-lg border bg-muted/50 p-4">
                <p className="text-sm font-medium">
                  Thank you for your answer!
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Sign up for a free account to get AI-powered feedback,
                  detailed grading, and model answers for your responses.
                </p>
              </div>
            )}
          </CardContent>
          <CardFooter className="flex gap-2">
            {!submitted ? (
              <Button
                onClick={handleSubmit}
                disabled={!answer.trim()}
              >
                Submit Answer
              </Button>
            ) : currentIndex < sampleQuestions.length - 1 ? (
              <Button onClick={handleNext}>Next Question</Button>
            ) : (
              <Button asChild>
                <Link href="/register">
                  Sign Up for Full Access
                </Link>
              </Button>
            )}
          </CardFooter>
        </Card>
      ) : (
        <Card className="text-center">
          <CardContent className="py-12">
            <p className="text-lg font-medium">
              You have completed all trial questions!
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Create a free account to unlock unlimited questions, AI tutoring,
              flashcards, and more.
            </p>
            <div className="mt-6">
              <Button asChild size="lg">
                <Link href="/register">Create Free Account</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
