"use client";

import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkles } from "lucide-react";
import { BurnoutIndicator } from "./BurnoutIndicator";

interface DailyBriefingCardProps {
  briefing?: {
    response: string;
    burnout_risk?: string;
    burnout_signals?: string[];
    priority_subjects?: string[];
  };
  isLoading: boolean;
}

export function DailyBriefingCard({
  briefing,
  isLoading,
}: DailyBriefingCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </CardContent>
      </Card>
    );
  }

  if (!briefing) return null;

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Sparkles className="h-5 w-5 text-primary" />
            Daily Briefing
          </CardTitle>
          <BurnoutIndicator
            riskLevel={briefing.burnout_risk}
            signals={briefing.burnout_signals}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <MarkdownRenderer content={briefing.response} />
        {briefing.priority_subjects && briefing.priority_subjects.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-2">
            <span className="text-xs font-medium text-muted-foreground">
              Priority:
            </span>
            {briefing.priority_subjects.map((s) => (
              <Badge key={s} variant="secondary">
                {s}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
