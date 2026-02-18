"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api-client";
import type { StudyGroup } from "../types";

export function useGroups() {
  return useQuery({
    queryKey: ["groups"],
    queryFn: () => api.get<{ groups: StudyGroup[] }>("/api/groups"),
    staleTime: 2 * 60 * 1000,
  });
}

export function useJoinGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: number) =>
      api.post(`/api/groups/${groupId}/join`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
    },
  });
}

export function useCreateGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description: string; subject: string }) =>
      api.post("/api/groups/create", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
    },
  });
}
