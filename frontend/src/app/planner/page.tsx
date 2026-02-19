"use client";

import { AdaptivePlanner } from "@/components/planner/AdaptivePlanner";

export default function PlannerPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Study Planner</h1>
        <p className="text-muted-foreground">
          AI-powered daily briefings, adaptive scheduling, and deadline tracking
        </p>
      </div>
      <AdaptivePlanner />
    </div>
  );
}
