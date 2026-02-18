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

export default function InsightsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["insights"],
    queryFn: () => api.get<InsightsData>("/api/insights"),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) return <LoadingSkeleton variant="page" />;

  if (error || !data) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
        <p className="text-destructive">
          Failed to load insights. Please try refreshing.
        </p>
      </div>
    );
  }

  const gradeLabels = Object.entries(data.grade_distribution);
  const latestTrends = data.trends.slice(-5);
  const topGaps = data.gaps.slice(0, 4);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Insights</h1>
        <p className="text-muted-foreground">
          Track your performance, identify gaps, and see predicted grades
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        {/* Grade Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Grade Distribution</CardTitle>
            <CardDescription>
              Breakdown of your grades across all subjects
            </CardDescription>
          </CardHeader>
          <CardContent>
            {gradeLabels.length > 0 ? (
              <div className="space-y-3">
                {gradeLabels.map(([grade, count]) => (
                  <div key={grade} className="flex items-center gap-3">
                    <span className="w-16 text-sm font-medium">{grade}</span>
                    <div className="flex-1 rounded-full bg-muted">
                      <div
                        className="h-3 rounded-full bg-primary transition-all"
                        style={{
                          width: `${Math.min(
                            100,
                            (count /
                              Math.max(
                                1,
                                ...gradeLabels.map(([, c]) => c)
                              )) *
                              100
                          )}%`,
                        }}
                      />
                    </div>
                    <span className="w-8 text-right text-sm text-muted-foreground">
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No grade data yet. Complete some study sessions to see your
                distribution.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Trend Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Trend Chart</CardTitle>
            <CardDescription>
              Your average scores over recent sessions
            </CardDescription>
          </CardHeader>
          <CardContent>
            {latestTrends.length > 0 ? (
              <div className="space-y-3">
                {latestTrends.map((point, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">{point.subject}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(point.date).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-24 rounded-full bg-muted">
                        <div
                          className="h-2 rounded-full bg-primary"
                          style={{ width: `${point.avg_score}%` }}
                        />
                      </div>
                      <span className="w-10 text-right text-sm font-medium">
                        {point.avg_score}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No trend data yet. Keep studying to track progress.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Gap Analysis */}
        <Card>
          <CardHeader>
            <CardTitle>Gap Analysis</CardTitle>
            <CardDescription>
              Topics where you need the most improvement
            </CardDescription>
          </CardHeader>
          <CardContent>
            {topGaps.length > 0 ? (
              <div className="space-y-4">
                {topGaps.map((gap, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-dashed p-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium">{gap.topic}</p>
                        <p className="text-xs text-muted-foreground">
                          {gap.subject}
                        </p>
                      </div>
                      <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">
                        {gap.score}%
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {gap.recommendation}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No gaps identified yet. Complete more sessions to find areas for
                improvement.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Predicted Grades */}
        <Card>
          <CardHeader>
            <CardTitle>Predicted Grades</CardTitle>
            <CardDescription>
              AI-predicted grades based on your performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.predicted_grades.length > 0 ? (
              <div className="space-y-3">
                {data.predicted_grades.map((pg, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <p className="text-sm font-medium">{pg.subject}</p>
                      <p className="text-xs text-muted-foreground">
                        Target: {pg.target} | Confidence:{" "}
                        {Math.round(pg.confidence * 100)}%
                      </p>
                    </div>
                    <span className="text-2xl font-bold">{pg.predicted}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Not enough data to predict grades. Keep studying!
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
