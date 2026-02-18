"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { InsightsData } from "@/lib/types";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

export default function AnalyticsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["insights"],
    queryFn: () => api.get<InsightsData>("/api/insights"),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return <LoadingSkeleton variant="page" />;
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">
            Deep-dive into your study performance and habits
          </p>
        </div>
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
          <p className="text-destructive">
            Failed to load analytics data. Please try refreshing.
          </p>
        </div>
      </div>
    );
  }

  const {
    study_allocation,
    command_term_stats,
    subject_stats,
    grade_distribution,
    total_answers,
    average_percentage,
    average_grade,
    insights,
  } = data;

  // Compute max values for bar scaling (guard against division by zero)
  const maxAllocation =
    study_allocation.length > 0
      ? Math.max(...study_allocation.map((s) => s.percentage))
      : 100;

  const maxCommandPct =
    command_term_stats.length > 0
      ? Math.max(...command_term_stats.map((c) => c.avg_percentage))
      : 100;

  const maxSubjectPct =
    subject_stats.length > 0
      ? Math.max(...subject_stats.map((s) => s.avg_percentage))
      : 100;

  // Sort grade distribution by key
  const gradeEntries = Object.entries(grade_distribution).sort(
    ([a], [b]) => Number(a) - Number(b)
  );
  const maxGradeCount =
    gradeEntries.length > 0
      ? Math.max(...gradeEntries.map(([, count]) => count))
      : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">
          Deep-dive into your study performance and habits
        </p>
      </div>

      {/* Overview stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Total Questions</CardDescription>
            <CardTitle className="text-3xl">{total_answers}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Average Score</CardDescription>
            <CardTitle className="text-3xl">
              {average_percentage.toFixed(0)}%
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Average Grade</CardDescription>
            <CardTitle className="text-3xl">
              {average_grade.toFixed(1)}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        {/* Study Time / Allocation */}
        <Card>
          <CardHeader>
            <CardTitle>Study Time</CardTitle>
            <CardDescription>
              How your study time is distributed across subjects
            </CardDescription>
          </CardHeader>
          <CardContent>
            {study_allocation.length === 0 ? (
              <EmptyState
                title="No allocation data"
                description="Study time allocation will appear once you have practiced across multiple subjects."
                className="border-0 p-4"
              />
            ) : (
              <div className="space-y-3">
                {study_allocation.map((item) => {
                  const pct =
                    maxAllocation > 0
                      ? (item.percentage / maxAllocation) * 100
                      : 0;
                  return (
                    <div key={item.subject} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{item.subject}</span>
                        <span className="text-muted-foreground">
                          {item.percentage.toFixed(0)}%
                        </span>
                      </div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-blue-500 transition-all"
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

        {/* Question Accuracy */}
        <Card>
          <CardHeader>
            <CardTitle>Question Accuracy</CardTitle>
            <CardDescription>
              Your accuracy rate across different command terms
            </CardDescription>
          </CardHeader>
          <CardContent>
            {command_term_stats.length === 0 ? (
              <EmptyState
                title="No accuracy data"
                description="Accuracy breakdowns will appear once you have answered questions with different command terms."
                className="border-0 p-4"
              />
            ) : (
              <div className="space-y-3">
                {command_term_stats.map((item) => {
                  const pct =
                    maxCommandPct > 0
                      ? (item.avg_percentage / maxCommandPct) * 100
                      : 0;
                  return (
                    <div key={item.command_term} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium capitalize">
                          {item.command_term}
                        </span>
                        <span className="text-muted-foreground">
                          {item.avg_percentage.toFixed(0)}% ({item.count})
                        </span>
                      </div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-green-500 transition-all"
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

        {/* Subject Comparison */}
        <Card>
          <CardHeader>
            <CardTitle>Subject Comparison</CardTitle>
            <CardDescription>
              Compare your performance across all IB subjects
            </CardDescription>
          </CardHeader>
          <CardContent>
            {subject_stats.length === 0 ? (
              <EmptyState
                title="No subject data"
                description="Subject comparisons will appear once you have studied multiple subjects."
                className="border-0 p-4"
              />
            ) : (
              <div className="space-y-3">
                {subject_stats.map((item) => {
                  const pct =
                    maxSubjectPct > 0
                      ? (item.avg_percentage / maxSubjectPct) * 100
                      : 0;
                  return (
                    <div key={item.subject} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{item.subject}</span>
                        <span className="text-muted-foreground">
                          {item.avg_percentage.toFixed(0)}% ({item.count} Qs)
                        </span>
                      </div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-purple-500 transition-all"
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

        {/* Streak History / Grade Distribution + Insights Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Streak History</CardTitle>
            <CardDescription>
              Your grade distribution and key insights
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-5">
              {/* Grade distribution mini chart */}
              {gradeEntries.length > 0 ? (
                <div>
                  <p className="mb-2 text-sm font-medium">
                    Grade Distribution
                  </p>
                  <div className="flex items-end gap-2">
                    {gradeEntries.map(([grade, count]) => {
                      const heightPct =
                        maxGradeCount > 0
                          ? (count / maxGradeCount) * 100
                          : 0;
                      return (
                        <div
                          key={grade}
                          className="flex flex-1 flex-col items-center gap-1"
                        >
                          <span className="text-xs text-muted-foreground">
                            {count}
                          </span>
                          <div
                            className="w-full rounded-t bg-primary transition-all"
                            style={{
                              height: `${Math.max(heightPct, 4)}px`,
                              minHeight: "4px",
                              maxHeight: "80px",
                            }}
                          />
                          <span className="text-xs font-medium">{grade}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No grade distribution data yet.
                </p>
              )}

              {/* Insights list */}
              {insights.length > 0 && (
                <div>
                  <p className="mb-2 text-sm font-medium">Key Insights</p>
                  <ul className="space-y-1.5">
                    {insights.slice(0, 4).map((insight, i) => (
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
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
