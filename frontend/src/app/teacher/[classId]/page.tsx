"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

interface GradeDistribution {
  class_name: string;
  distribution: Record<string, number>;
}

interface AtRiskStudent {
  id: string;
  name: string;
  current_grade: number;
  risk_level: "high" | "medium" | "low";
  reason: string;
}

interface AtRiskData {
  students: AtRiskStudent[];
}

interface TopicGap {
  topic: string;
  coverage: number;
  class_avg: number;
  needs_attention: boolean;
}

interface TopicGapsData {
  gaps: TopicGap[];
}

export default function ClassDetailPage() {
  const params = useParams<{ classId: string }>();
  const classId = params.classId;

  const {
    data: gradeData,
    isLoading: gradesLoading,
    error: gradesError,
  } = useQuery({
    queryKey: ["teacher", "class", classId, "grades"],
    queryFn: () =>
      api.get<GradeDistribution>(
        `/api/teacher/class/${classId}/grade-distribution`
      ),
    staleTime: 60 * 1000,
    enabled: !!classId,
  });

  const {
    data: atRiskData,
    isLoading: atRiskLoading,
    error: atRiskError,
  } = useQuery({
    queryKey: ["teacher", "class", classId, "at-risk"],
    queryFn: () =>
      api.get<AtRiskData>(`/api/teacher/class/${classId}/at-risk`),
    staleTime: 60 * 1000,
    enabled: !!classId,
  });

  const {
    data: topicData,
    isLoading: topicsLoading,
    error: topicsError,
  } = useQuery({
    queryKey: ["teacher", "class", classId, "topic-gaps"],
    queryFn: () =>
      api.get<TopicGapsData>(`/api/teacher/class/${classId}/topic-gaps`),
    staleTime: 60 * 1000,
    enabled: !!classId,
  });

  const isLoading = gradesLoading || atRiskLoading || topicsLoading;

  if (isLoading) {
    return <LoadingSkeleton variant="page" />;
  }

  const hasError = gradesError || atRiskError || topicsError;

  // Find the max value in the grade distribution for scaling
  const gradeEntries = gradeData?.distribution
    ? Object.entries(gradeData.distribution).sort(
        ([a], [b]) => Number(a) - Number(b)
      )
    : [];
  const maxGradeCount =
    gradeEntries.length > 0
      ? Math.max(...gradeEntries.map(([, count]) => count))
      : 0;

  const riskColorMap: Record<string, string> = {
    high: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    medium:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    low: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  };

  return (
    <div className="space-y-6">
      {/* Back link */}
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="sm">
          <Link href="/teacher">Back to Dashboard</Link>
        </Button>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">
          {gradeData?.class_name ?? `Class: ${classId}`}
        </h1>
        <p className="text-muted-foreground">
          Student performance overview and class management
        </p>
      </div>

      {hasError && (
        <div className="rounded-xl border border-danger-500/20 bg-danger-50 p-4 text-center dark:bg-danger-500/10">
          <p className="text-sm text-danger-700 dark:text-danger-500">
            Some data failed to load. Showing available information below.
          </p>
        </div>
      )}

      {/* Grade Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Grade Distribution</CardTitle>
          <CardDescription>
            How grades are distributed across the class (IB scale 1-7)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {gradesError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load grade distribution.
            </p>
          ) : gradeEntries.length === 0 ? (
            <EmptyState
              title="No grade data"
              description="Grade distribution will appear once students have completed assessments."
            />
          ) : (
            <div className="space-y-3">
              {gradeEntries.map(([grade, count]) => {
                const pct =
                  maxGradeCount > 0 ? (count / maxGradeCount) * 100 : 0;
                return (
                  <div key={grade} className="flex items-center gap-3">
                    <span className="w-16 text-right text-sm font-medium">
                      Grade {grade}
                    </span>
                    <div className="relative h-8 flex-1 overflow-hidden rounded-md bg-muted">
                      <div
                        className="absolute inset-y-0 left-0 rounded-md bg-primary transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-10 text-sm text-muted-foreground">
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* At-Risk Students */}
      <Card>
        <CardHeader>
          <CardTitle>At-Risk Students</CardTitle>
          <CardDescription>
            Students who may need additional support
          </CardDescription>
        </CardHeader>
        <CardContent>
          {atRiskError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load at-risk student data.
            </p>
          ) : !atRiskData?.students || atRiskData.students.length === 0 ? (
            <EmptyState
              title="No at-risk students"
              description="All students are currently performing within expected ranges."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium">Student</th>
                    <th className="pb-2 font-medium">Current Grade</th>
                    <th className="pb-2 font-medium">Risk Level</th>
                    <th className="pb-2 font-medium">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {atRiskData.students.map((student) => (
                    <tr key={student.id}>
                      <td className="py-3 font-medium">{student.name}</td>
                      <td className="py-3">{student.current_grade}</td>
                      <td className="py-3">
                        <span
                          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${riskColorMap[student.risk_level] ?? ""}`}
                        >
                          {student.risk_level}
                        </span>
                      </td>
                      <td className="py-3 text-muted-foreground">
                        {student.reason}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Topic Gaps */}
      <Card>
        <CardHeader>
          <CardTitle>Topic Gaps</CardTitle>
          <CardDescription>
            Topics that need more attention based on class performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          {topicsError ? (
            <p className="text-sm text-muted-foreground">
              Failed to load topic gap data.
            </p>
          ) : !topicData?.gaps || topicData.gaps.length === 0 ? (
            <EmptyState
              title="No topic gaps identified"
              description="All topics have adequate coverage. Keep up the good work."
            />
          ) : (
            <div className="space-y-3">
              {topicData.gaps.map((gap) => (
                <div
                  key={gap.topic}
                  className={`flex items-center justify-between rounded-lg border p-3 ${
                    gap.needs_attention
                      ? "border-yellow-300 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-900/10"
                      : ""
                  }`}
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium">{gap.topic}</p>
                    <p className="text-xs text-muted-foreground">
                      Coverage: {gap.coverage}% | Class Avg:{" "}
                      {gap.class_avg.toFixed(1)}%
                    </p>
                  </div>
                  {gap.needs_attention && (
                    <span className="shrink-0 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                      Needs Attention
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
