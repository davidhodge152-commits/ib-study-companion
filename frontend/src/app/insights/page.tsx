"use client";

import { useInsights, usePredictedGrades } from "@/lib/hooks/useInsights";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";

export default function InsightsPage() {
  const { data, isLoading, error } = useInsights();
  const { data: predictions } = usePredictedGrades();

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
  const subjectStats = data.subject_stats || [];
  const topGaps = (data.gaps || []).slice(0, 4);

  // Build predicted grades from separate endpoint
  const predictedGrades = predictions?.by_subject
    ? Object.entries(predictions.by_subject).map(([subject, predicted]) => ({
        subject,
        predicted,
      }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Insights</h1>
        <p className="text-muted-foreground">
          Track your performance, identify gaps, and see predicted grades
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-3xl font-bold">{data.total_answers}</p>
            <p className="text-sm text-muted-foreground">Total Answers</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-3xl font-bold">{data.average_grade || 0}</p>
            <p className="text-sm text-muted-foreground">Average Grade</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-3xl font-bold">{data.average_percentage || 0}%</p>
            <p className="text-sm text-muted-foreground">Average Score</p>
          </CardContent>
        </Card>
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

        {/* Subject Performance */}
        <Card>
          <CardHeader>
            <CardTitle>Subject Performance</CardTitle>
            <CardDescription>
              Your average scores by subject
            </CardDescription>
          </CardHeader>
          <CardContent>
            {subjectStats.length > 0 ? (
              <div className="space-y-3">
                {subjectStats.map((stat, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">{stat.subject}</p>
                      <p className="text-xs text-muted-foreground">
                        {stat.count} question{stat.count !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-24 rounded-full bg-muted">
                        <div
                          className="h-2 rounded-full bg-primary"
                          style={{ width: `${stat.avg_percentage}%` }}
                        />
                      </div>
                      <span className="w-10 text-right text-sm font-medium">
                        {Math.round(stat.avg_percentage)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No subject data yet. Keep studying to track progress.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Gap Analysis */}
        <Card>
          <CardHeader>
            <CardTitle>Gap Analysis</CardTitle>
            <CardDescription>
              Subjects where you need the most improvement
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
                        <p className="text-sm font-medium">{gap.subject}</p>
                        <p className="text-xs text-muted-foreground">
                          Target: {gap.target_grade} | Current:{" "}
                          {Math.round(gap.current_avg)}%
                        </p>
                      </div>
                      <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">
                        Gap: {gap.gap}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Status: {gap.status}
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
              {predictions?.predicted_total !== undefined && (
                <span className="ml-1 font-medium">
                  (Predicted total: {predictions.predicted_total})
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {predictedGrades.length > 0 ? (
              <div className="space-y-3">
                {predictedGrades.map((pg, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <p className="text-sm font-medium">{pg.subject}</p>
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

      {/* AI Insights */}
      {data.insights && data.insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>AI Study Insights</CardTitle>
            <CardDescription>
              Personalized recommendations based on your study patterns
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.insights.map((insight, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 text-primary">•</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
