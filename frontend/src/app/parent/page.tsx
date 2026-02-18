"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { DashboardData, InsightsData } from "@/lib/types";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

export default function ParentDashboardPage() {
  const {
    data: dashboardData,
    isLoading: dashLoading,
    error: dashError,
  } = useQuery({
    queryKey: ["parent", "dashboard"],
    queryFn: () => api.get<DashboardData>("/api/dashboard"),
    staleTime: 60 * 1000,
  });

  const {
    data: insightsData,
    isLoading: insightsLoading,
    error: insightsError,
  } = useQuery({
    queryKey: ["parent", "insights"],
    queryFn: () => api.get<InsightsData>("/api/insights"),
    staleTime: 5 * 60 * 1000,
  });

  const isLoading = dashLoading || insightsLoading;

  if (isLoading) {
    return <LoadingSkeleton variant="page" />;
  }

  const hasError = dashError || insightsError;
  const stats = dashboardData?.stats;
  const recentActivity = dashboardData?.recent_activity ?? [];
  const subjectStats = insightsData?.subject_stats ?? [];

  // Find the maximum avg_percentage for scaling subject bars
  const maxSubjectPct =
    subjectStats.length > 0
      ? Math.max(...subjectStats.map((s) => s.avg_percentage))
      : 100;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Parent Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your child&apos;s IB progress and study habits
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/parent/settings">Settings</Link>
        </Button>
      </div>

      {hasError && (
        <div className="rounded-xl border border-danger-500/20 bg-danger-50 p-4 text-center dark:bg-danger-500/10">
          <p className="text-sm text-danger-700 dark:text-danger-500">
            Some data could not be loaded. Showing available information.
          </p>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Study Streak</CardDescription>
            <CardTitle className="text-3xl">
              {stats ? `${stats.current_streak} days` : "-- days"}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Avg. Grade</CardDescription>
            <CardTitle className="text-3xl">
              {stats ? stats.avg_grade.toFixed(1) : "--"}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Questions This Week</CardDescription>
            <CardTitle className="text-3xl">
              {stats ? stats.total_questions : "--"}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Subject Performance */}
        <Card>
          <CardHeader>
            <CardTitle>Subject Performance</CardTitle>
            <CardDescription>
              How your child is performing across their IB subjects
            </CardDescription>
          </CardHeader>
          <CardContent>
            {subjectStats.length === 0 ? (
              <EmptyState
                title="No subject data yet"
                description="Subject performance data will appear here once your child has completed enough study sessions."
                className="border-0 p-6"
              />
            ) : (
              <div className="space-y-3">
                {subjectStats.map((subject) => {
                  const pct =
                    maxSubjectPct > 0
                      ? (subject.avg_percentage / maxSubjectPct) * 100
                      : 0;
                  return (
                    <div key={subject.subject} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{subject.subject}</span>
                        <span className="text-muted-foreground">
                          {subject.avg_percentage.toFixed(0)}% ({subject.count}{" "}
                          Qs)
                        </span>
                      </div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Your child&apos;s latest study sessions and milestones
            </CardDescription>
          </CardHeader>
          <CardContent>
            {recentActivity.length === 0 ? (
              <EmptyState
                title="No recent activity"
                description="Recent activity will appear here as your child uses the platform."
                className="border-0 p-6"
              />
            ) : (
              <div className="space-y-3">
                {recentActivity.slice(0, 8).map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start gap-3 rounded-lg border p-3"
                  >
                    <div
                      className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${
                        item.type === "study"
                          ? "bg-blue-500"
                          : item.type === "flashcard"
                            ? "bg-green-500"
                            : item.type === "tutor"
                              ? "bg-purple-500"
                              : "bg-gray-400"
                      }`}
                    />
                    <div className="flex-1 space-y-0.5">
                      <p className="text-sm">{item.description}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        {item.subject && <span>{item.subject}</span>}
                        <span>
                          {new Date(item.timestamp).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Weekly Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Weekly Summary</CardTitle>
          <CardDescription>
            An overview of study activity for the current week
          </CardDescription>
        </CardHeader>
        <CardContent>
          {insightsData ? (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-2xl font-bold">
                    {insightsData.total_answers}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Total Questions Answered
                  </p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-2xl font-bold">
                    {insightsData.average_percentage.toFixed(0)}%
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Average Score
                  </p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-2xl font-bold">
                    {insightsData.subject_stats.length}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Subjects Studied
                  </p>
                </div>
              </div>
              {insightsData.insights.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Key Insights</p>
                  <ul className="space-y-1">
                    {insightsData.insights.slice(0, 3).map((insight, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-muted-foreground"
                      >
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                        {insight}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-32 items-center justify-center rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Weekly summary will appear once enough data is available.
              </p>
            </div>
          )}
        </CardContent>
        <CardFooter>
          <p className="text-xs text-muted-foreground">
            Email summaries can be configured in{" "}
            <Link href="/parent/settings" className="text-primary underline">
              settings
            </Link>
            .
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
