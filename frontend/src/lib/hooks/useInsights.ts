"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "../api-client";
import type { InsightsData, PredictedGrade } from "../types";

export function useInsights() {
  return useQuery({
    queryKey: ["insights"],
    queryFn: () => api.get<InsightsData>("/api/insights"),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePredictedGrades() {
  return useQuery({
    queryKey: ["insights", "predictions"],
    queryFn: () =>
      api.get<{ predicted_total: number; by_subject: Record<string, number> }>(
        "/api/insights/predictions"
      ),
    staleTime: 10 * 60 * 1000,
  });
}
