"use client";

import { useState } from "react";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSmartPlan, useGenerateSmartPlan } from "@/lib/hooks/useAdaptivePlanner";
import { PlanConfigDialog } from "./PlanConfigDialog";
import { CalendarDays, RefreshCw } from "lucide-react";

export function SmartPlanView() {
  const { data, isLoading } = useSmartPlan();
  const generatePlan = useGenerateSmartPlan();
  const [showConfig, setShowConfig] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const plan = data?.plan;

  if (!plan) {
    return (
      <>
        <EmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title="No study plan yet"
          description="Generate an AI-powered weekly study plan based on your subjects, deadlines, and mastery levels."
          action={
            <Button onClick={() => setShowConfig(true)}>
              Generate Plan
            </Button>
          }
        />
        <PlanConfigDialog
          open={showConfig}
          onOpenChange={setShowConfig}
          onGenerate={(params) => {
            generatePlan.mutate(params);
            setShowConfig(false);
          }}
          isPending={generatePlan.isPending}
        />
      </>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          AI-generated study plan
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowConfig(true)}
          disabled={generatePlan.isPending}
        >
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          {generatePlan.isPending ? "Generating..." : "Regenerate"}
        </Button>
      </div>
      <Card>
        <CardContent className="pt-6">
          <MarkdownRenderer content={plan.response} />
        </CardContent>
      </Card>
      <PlanConfigDialog
        open={showConfig}
        onOpenChange={setShowConfig}
        onGenerate={(params) => {
          generatePlan.mutate(params);
          setShowConfig(false);
        }}
        isPending={generatePlan.isPending}
      />
    </div>
  );
}
