"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
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

interface TeacherClass {
  id: string;
  name: string;
  student_count: number;
  avg_grade: number;
}

interface TeacherStats {
  class_count: number;
  total_students: number;
  classes: TeacherClass[];
}

export default function TeacherDashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["teacher", "stats"],
    queryFn: () => api.get<TeacherStats>("/api/teacher/stats"),
    staleTime: 60 * 1000,
  });

  if (isLoading) {
    return <LoadingSkeleton variant="page" />;
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Teacher Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor student progress and manage your IB classes
          </p>
        </div>
        <div className="rounded-xl border border-danger-500/20 bg-danger-50 p-6 text-center dark:bg-danger-500/10">
          <p className="text-danger-700 dark:text-danger-500">
            Failed to load teacher data. Please try refreshing.
          </p>
        </div>
      </div>
    );
  }

  const avgGrade =
    data.classes.length > 0
      ? (
          data.classes.reduce((sum, c) => sum + c.avg_grade, 0) /
          data.classes.length
        ).toFixed(1)
      : "N/A";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Teacher Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor student progress and manage your IB classes
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Total Students</CardDescription>
            <CardTitle className="text-3xl">{data.total_students}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Active Classes</CardDescription>
            <CardTitle className="text-3xl">{data.class_count}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Average Grade</CardDescription>
            <CardTitle className="text-3xl">{avgGrade}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Class Cards Grid */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Your Classes</h2>
        {data.classes.length === 0 ? (
          <EmptyState
            title="No classes yet"
            description="You haven't created any classes. Classes will appear here once they are set up."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.classes.map((cls) => (
              <Card
                key={cls.id}
                className="transition-shadow hover:shadow-md"
              >
                <CardHeader>
                  <CardTitle className="text-lg">{cls.name}</CardTitle>
                  <CardDescription>
                    {cls.student_count} students
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      Class Average
                    </span>
                    <span className="text-xl font-bold">
                      {cls.avg_grade.toFixed(1)}
                    </span>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button asChild variant="outline" className="w-full">
                    <Link href={`/teacher/${cls.id}`}>View Class</Link>
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
