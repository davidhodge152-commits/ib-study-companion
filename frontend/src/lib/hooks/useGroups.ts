"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
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
      toast.success("Joined group!");
    },
    onError: () => {
      toast.error("Failed to join group.");
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
      toast.success("Group created!");
    },
    onError: () => {
      toast.error("Failed to create group.");
    },
  });
}

export function useLeaveGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: number) =>
      api.post(`/api/groups/${groupId}/leave`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      toast.success("Left group.");
    },
    onError: () => {
      toast.error("Failed to leave group.");
    },
  });
}

export function useDeleteGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: number) =>
      api.delete(`/api/groups/${groupId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      toast.success("Group deleted.");
    },
    onError: () => {
      toast.error("Failed to delete group.");
    },
  });
}
