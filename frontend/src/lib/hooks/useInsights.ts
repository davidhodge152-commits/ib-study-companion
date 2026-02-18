"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "../api-client";
import type { InsightsData } from "../types";

export function useInsights() {
  return useQuery({
    queryKey: ["insights"],
    queryFn: () => api.get<InsightsData>("/api/insights"),
    staleTime: 5 * 60 * 1000,
  });
}
