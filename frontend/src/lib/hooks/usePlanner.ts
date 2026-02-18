"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api-client";
import type { PlannerTask } from "../types";

export function usePlannerTasks() {
  return useQuery({
    queryKey: ["planner", "tasks"],
    queryFn: () => api.get<{ tasks: PlannerTask[] }>("/api/planner/tasks"),
    staleTime: 2 * 60 * 1000,
  });
}

export function useToggleTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, completed }: { id: number; completed: boolean }) =>
      api.patch(`/api/planner/tasks/${id}`, { completed }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["planner"] });
    },
  });
}

export function useGenerateStudyPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/api/planner/generate"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["planner"] });
    },
  });
}
