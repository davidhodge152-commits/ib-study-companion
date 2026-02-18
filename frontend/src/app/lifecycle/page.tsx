"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface PhaseItem {
  id: string;
  label: string;
}

interface Phase {
  title: string;
  description: string;
  items: PhaseItem[];
}

const phases: Phase[] = [
  {
    title: "Year 1 - Foundation",
    description: "Build strong subject foundations and study habits",
    items: [
      { id: "y1f-subject-selection", label: "Subject selection guidance" },
      { id: "y1f-core-skills", label: "Core skills development" },
      { id: "y1f-ia-ee-intro", label: "Introduction to IA/EE topics" },
      { id: "y1f-cas-planning", label: "CAS planning" },
    ],
  },
  {
    title: "Year 1 - Mid-Year",
    description: "Deepen understanding and start internal assessments",
    items: [
      { id: "y1m-ia-drafting", label: "IA research and drafting" },
      { id: "y1m-tok-essay", label: "TOK essay exploration" },
      { id: "y1m-mock-prep", label: "Mock exam preparation" },
      { id: "y1m-cas-tracking", label: "CAS activity tracking" },
    ],
  },
  {
    title: "Year 2 - Intensive",
    description: "Finalize IAs and prepare for final examinations",
    items: [
      { id: "y2i-ia-final", label: "IA final submissions" },
      { id: "y2i-ee-completion", label: "Extended Essay completion" },
      { id: "y2i-tok-presentation", label: "TOK presentation prep" },
      { id: "y2i-past-papers", label: "Past paper practice" },
    ],
  },
  {
    title: "Year 2 - Exam Season",
    description: "Final revision and exam execution",
    items: [
      { id: "y2e-revision-plans", label: "Subject-specific revision plans" },
      { id: "y2e-exam-technique", label: "Exam technique refinement" },
      { id: "y2e-stress-mgmt", label: "Stress management resources" },
      { id: "y2e-results-prep", label: "Results day preparation" },
    ],
  },
];

function getNextExamDate(): Date {
  const now = new Date();
  const year = now.getFullYear();

  // IB exams are in May and November
  const mayExam = new Date(year, 4, 1); // May 1
  const novExam = new Date(year, 10, 1); // November 1

  if (now < mayExam) return mayExam;
  if (now < novExam) return novExam;
  // Next year May
  return new Date(year + 1, 4, 1);
}

function getDaysUntil(target: Date): number {
  const now = new Date();
  const diff = target.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

export default function LifecyclePage() {
  const queryClient = useQueryClient();

  // Track completed milestones in local state (persisted to localStorage)
  const [completed, setCompleted] = useState<Record<string, boolean>>({});
  const [examDate, setExamDate] = useState<Date>(getNextExamDate());
  const [daysLeft, setDaysLeft] = useState<number>(getDaysUntil(getNextExamDate()));

  // Load persisted milestones on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem("ib-lifecycle-milestones");
      if (stored) {
        setCompleted(JSON.parse(stored));
      }
    } catch {
      // ignore parse errors
    }
  }, []);

  // Update countdown every minute
  useEffect(() => {
    const nextExam = getNextExamDate();
    setExamDate(nextExam);
    setDaysLeft(getDaysUntil(nextExam));

    const interval = setInterval(() => {
      setDaysLeft(getDaysUntil(nextExam));
    }, 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const milestoneMutation = useMutation({
    mutationFn: (data: { milestone_id: string; completed: boolean }) =>
      api.post("/api/lifecycle/milestone", data),
    onError: () => {
      // Revert optimistic update on error - no-op here since we already saved
    },
  });

  const toggleMilestone = useCallback(
    (milestoneId: string) => {
      setCompleted((prev) => {
        const newCompleted = { ...prev, [milestoneId]: !prev[milestoneId] };
        // Persist to localStorage
        try {
          localStorage.setItem(
            "ib-lifecycle-milestones",
            JSON.stringify(newCompleted)
          );
        } catch {
          // ignore storage errors
        }
        // Fire API call
        milestoneMutation.mutate({
          milestone_id: milestoneId,
          completed: newCompleted[milestoneId],
        });
        return newCompleted;
      });
    },
    [milestoneMutation]
  );

  // Calculate per-phase progress
  const phaseProgress = useMemo(() => {
    return phases.map((phase) => {
      const total = phase.items.length;
      const done = phase.items.filter((item) => completed[item.id]).length;
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
      return { done, total, pct };
    });
  }, [completed]);

  // Overall progress
  const totalItems = phases.reduce((sum, p) => sum + p.items.length, 0);
  const totalDone = Object.values(completed).filter(Boolean).length;
  const overallPct = totalItems > 0 ? Math.round((totalDone / totalItems) * 100) : 0;

  const examMonth = examDate.toLocaleString("default", {
    month: "long",
    year: "numeric",
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">IB Lifecycle</h1>
        <p className="text-muted-foreground">
          Navigate every phase of your IB Diploma journey
        </p>
      </div>

      {/* Exam Countdown */}
      <Card>
        <CardContent className="py-6">
          <div className="flex flex-col items-center gap-2 text-center sm:flex-row sm:justify-between sm:text-left">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Next Exam Session
              </p>
              <p className="text-lg font-semibold">{examMonth}</p>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold tabular-nums">
                {daysLeft}
              </span>
              <span className="text-lg text-muted-foreground">
                days remaining
              </span>
            </div>
            <div className="w-full sm:w-48">
              <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                <span>Overall Progress</span>
                <span>{overallPct}%</span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${overallPct}%` }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <div className="relative">
        {/* Timeline connector */}
        <div className="absolute left-6 top-0 hidden h-full w-0.5 bg-border md:block" />

        <div className="space-y-6">
          {phases.map((phase, i) => {
            const progress = phaseProgress[i];
            return (
              <div key={i} className="relative md:pl-16">
                {/* Timeline dot */}
                <div
                  className={`absolute left-4 top-8 hidden h-5 w-5 rounded-full border-2 md:block ${
                    progress.pct === 100
                      ? "border-green-500 bg-green-100 dark:bg-green-900/30"
                      : progress.pct > 0
                        ? "border-primary bg-primary/10"
                        : "border-primary bg-background"
                  }`}
                />

                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <CardTitle>{phase.title}</CardTitle>
                        <CardDescription>{phase.description}</CardDescription>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="text-sm font-medium">
                          {progress.done}/{progress.total}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {progress.pct}% complete
                        </p>
                      </div>
                    </div>
                    {/* Phase progress bar */}
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full transition-all ${
                          progress.pct === 100 ? "bg-green-500" : "bg-primary"
                        }`}
                        style={{ width: `${progress.pct}%` }}
                      />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {phase.items.map((item) => {
                        const isChecked = !!completed[item.id];
                        return (
                          <li key={item.id}>
                            <button
                              type="button"
                              onClick={() => toggleMilestone(item.id)}
                              className="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted/50"
                            >
                              <span
                                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors ${
                                  isChecked
                                    ? "border-primary bg-primary text-primary-foreground"
                                    : "border-muted-foreground/30 bg-background"
                                }`}
                              >
                                {isChecked && (
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth={3}
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    className="h-3 w-3"
                                  >
                                    <polyline points="20 6 9 17 4 12" />
                                  </svg>
                                )}
                              </span>
                              <span
                                className={
                                  isChecked
                                    ? "text-muted-foreground line-through"
                                    : "text-foreground"
                                }
                              >
                                {item.label}
                              </span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
