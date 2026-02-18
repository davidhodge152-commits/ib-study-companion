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
    onMutate: async ({ id, completed }) => {
      // Cancel any outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ["planner", "tasks"] });

      // Snapshot the previous value
      const previous = queryClient.getQueryData(["planner", "tasks"]);

      // Optimistically update the task's completed status
      queryClient.setQueryData(
        ["planner", "tasks"],
        (old: { tasks: PlannerTask[] } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            tasks: old.tasks.map((task) =>
              task.id === id ? { ...task, completed } : task
            ),
          };
        }
      );

      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Roll back to the previous value on error
      if (context?.previous) {
        queryClient.setQueryData(["planner", "tasks"], context.previous);
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure server state
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
