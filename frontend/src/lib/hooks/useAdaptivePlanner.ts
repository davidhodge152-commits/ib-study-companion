"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../api-client";
import type {
  DailyBriefing,
  SmartPlan,
  BurnoutCheck,
  StudyDeadline,
  ReprioritizeResponse,
} from "../types/planner";

export function useDailyBriefing() {
  return useQuery({
    queryKey: ["executive", "briefing"],
    queryFn: () => api.get<DailyBriefing>("/api/executive/daily-briefing"),
    staleTime: 5 * 60 * 1000,
  });
}

export function useSmartPlan() {
  return useQuery({
    queryKey: ["executive", "smart-plan"],
    queryFn: () => api.get<{ plan: SmartPlan | null }>("/api/executive/smart-plan"),
    staleTime: 5 * 60 * 1000,
  });
}

export function useGenerateSmartPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { days_ahead?: number; daily_minutes?: number }) =>
      api.post<SmartPlan>("/api/executive/generate-plan", params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["executive", "smart-plan"] });
      toast.success("Study plan generated!");
    },
    onError: () => {
      toast.error("Failed to generate plan. Please try again.");
    },
  });
}

export function useBurnoutCheck() {
  return useQuery({
    queryKey: ["executive", "burnout"],
    queryFn: () => api.get<BurnoutCheck>("/api/executive/burnout-check"),
    staleTime: 10 * 60 * 1000,
  });
}

export function useReprioritize() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (event: string) =>
      api.post<ReprioritizeResponse>("/api/executive/reprioritize", { event }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["executive"] });
      queryClient.invalidateQueries({ queryKey: ["planner"] });
      toast.success("Plan reprioritized!");
    },
    onError: () => {
      toast.error("Failed to reprioritize. Please try again.");
    },
  });
}

export function useDeadlines() {
  return useQuery({
    queryKey: ["deadlines"],
    queryFn: () => api.get<{ deadlines: StudyDeadline[] }>("/api/deadlines"),
    staleTime: 2 * 60 * 1000,
  });
}

export function useCreateDeadline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      title: string;
      subject: string;
      deadline_type: string;
      due_date: string;
      importance: string;
    }) => api.post("/api/deadlines", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deadlines"] });
      toast.success("Deadline added!");
    },
    onError: () => {
      toast.error("Failed to create deadline.");
    },
  });
}

export function useUpdateDeadline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: {
      id: number;
      completed?: boolean;
      title?: string;
      due_date?: string;
    }) => api.patch(`/api/deadlines/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deadlines"] });
    },
    onError: () => {
      toast.error("Failed to update deadline.");
    },
  });
}
