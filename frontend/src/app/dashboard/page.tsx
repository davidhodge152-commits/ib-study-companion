"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { DashboardData } from "@/lib/types";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { ProgressChart } from "@/components/dashboard/ProgressChart";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardData>("/api/dashboard"),
    staleTime: 60 * 1000,
  });

  if (isLoading) return <LoadingSkeleton variant="page" />;

  if (error || !data) {
    return (
      <div className="rounded-xl border border-danger-500/20 bg-danger-50 p-6 text-center dark:bg-danger-500/10">
        <p className="text-danger-700 dark:text-danger-500">
          Failed to load dashboard data. Please try refreshing.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Command Center</h1>
        <p className="text-muted-foreground">Your study overview at a glance</p>
      </div>

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
    </div>
  );
}
