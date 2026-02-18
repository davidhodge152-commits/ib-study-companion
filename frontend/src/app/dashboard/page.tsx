"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Upload,
  BookOpen,
  Layers,
  MessageCircle,
  RefreshCw,
} from "lucide-react";
import { api, ApiRequestError } from "@/lib/api-client";
import type { DashboardData } from "@/lib/types";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { ProgressChart } from "@/components/dashboard/ProgressChart";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Button } from "@/components/ui/button";

/** Check if the dashboard data indicates a brand-new user with zero activity. */
function isNewUser(data: DashboardData): boolean {
  const s = data.stats;
  if (!s) return true;
  return (
    (s.total_questions ?? 0) === 0 &&
    (s.avg_grade ?? 0) === 0 &&
    (s.current_streak ?? 0) === 0 &&
    (!data.recent_activity || data.recent_activity.length === 0)
  );
}

function NewUserWelcome() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-dashed border-primary/30 bg-primary/5 p-8 text-center">
        <h2 className="text-xl font-semibold">
          Welcome to your IB Study Companion!
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          Get started by uploading your study materials, then let AI generate
          questions and flashcards tailored to your subjects.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          href="/upload"
          className="group flex flex-col items-center gap-3 rounded-xl border p-6 text-center transition-colors hover:border-primary hover:bg-primary/5"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
            <Upload className="h-6 w-6" />
          </div>
          <div>
            <p className="font-medium">Upload Notes</p>
            <p className="text-xs text-muted-foreground">
              Add past papers, notes, or textbook excerpts
            </p>
          </div>
        </Link>

        <Link
          href="/study"
          className="group flex flex-col items-center gap-3 rounded-xl border p-6 text-center transition-colors hover:border-primary hover:bg-primary/5"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
            <BookOpen className="h-6 w-6" />
          </div>
          <div>
            <p className="font-medium">Start Studying</p>
            <p className="text-xs text-muted-foreground">
              Generate IB-style questions with AI feedback
            </p>
          </div>
        </Link>

        <Link
          href="/flashcards"
          className="group flex flex-col items-center gap-3 rounded-xl border p-6 text-center transition-colors hover:border-primary hover:bg-primary/5"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
            <Layers className="h-6 w-6" />
          </div>
          <div>
            <p className="font-medium">Flashcards</p>
            <p className="text-xs text-muted-foreground">
              Review with spaced repetition
            </p>
          </div>
        </Link>

        <Link
          href="/tutor"
          className="group flex flex-col items-center gap-3 rounded-xl border p-6 text-center transition-colors hover:border-primary hover:bg-primary/5"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
            <MessageCircle className="h-6 w-6" />
          </div>
          <div>
            <p className="font-medium">AI Tutor</p>
            <p className="text-xs text-muted-foreground">
              Ask anything about your IB subjects
            </p>
          </div>
        </Link>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardData>("/api/dashboard"),
    staleTime: 60 * 1000,
    retry: (count, err) => {
      // Don't retry if user needs onboarding
      if (err instanceof ApiRequestError && err.status === 404) return false;
      return count < 2;
    },
  });

  // Redirect to onboarding if profile is missing
  useEffect(() => {
    if (error instanceof ApiRequestError && error.status === 404) {
      router.replace("/onboarding");
    }
  }, [error, router]);

  if (isLoading) return <LoadingSkeleton variant="page" />;

  if (error || !data) {
    // If it's a 404 (onboarding needed), show nothing while redirecting
    if (error instanceof ApiRequestError && error.status === 404) {
      return <LoadingSkeleton variant="page" />;
    }
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
        <p className="text-destructive">
          Failed to load dashboard data.
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-3"
          onClick={() =>
            queryClient.invalidateQueries({ queryKey: ["dashboard"] })
          }
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Command Center</h1>
        <p className="text-muted-foreground">Your study overview at a glance</p>
      </div>

      {isNewUser(data) ? (
        <NewUserWelcome />
      ) : (
        <>
          <ErrorBoundary>
            <StatsCards stats={data.stats} />
          </ErrorBoundary>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ErrorBoundary>
                <ProgressChart data={data.progress} />
              </ErrorBoundary>
            </div>
            <div>
              <ErrorBoundary>
                <QuickActions />
              </ErrorBoundary>
            </div>
          </div>

          <ErrorBoundary>
            <RecentActivity items={data.recent_activity} />
          </ErrorBoundary>
        </>
      )}
    </div>
  );
}
