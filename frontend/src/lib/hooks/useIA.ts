"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../api-client";
import type {
  CourseworkSession,
  CourseworkSessionDetail,
  FeasibilityResult,
  DraftReviewResult,
  DataAnalysisResult,
} from "../types/ia";

export function useCourseworkSessions() {
  return useQuery({
    queryKey: ["coursework", "sessions"],
    queryFn: () =>
      api.get<{ sessions: CourseworkSession[] }>("/api/coursework/sessions"),
    staleTime: 2 * 60 * 1000,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      doc_type: string;
      subject: string;
      title: string;
    }) =>
      api.post<{ success: boolean; session_id: number }>(
        "/api/coursework/sessions",
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coursework", "sessions"] });
      toast.success("IA session created!");
    },
    onError: () => {
      toast.error("Failed to create session.");
    },
  });
}

export function useCourseworkSession(sessionId: number | null) {
  return useQuery({
    queryKey: ["coursework", "session", sessionId],
    queryFn: () =>
      api.get<CourseworkSessionDetail>(
        `/api/coursework/sessions/${sessionId}`
      ),
    enabled: !!sessionId,
    staleTime: 60 * 1000,
  });
}

export function useCheckFeasibility() {
  return useMutation({
    mutationFn: (data: {
      topic: string;
      subject: string;
      doc_type: string;
      school_constraints?: string;
    }) =>
      api.post<FeasibilityResult>("/api/coursework/check-feasibility", data),
    onError: () => {
      toast.error("Failed to check feasibility.");
    },
  });
}

export function useReviewDraft() {
  return useMutation({
    mutationFn: (data: {
      text: string;
      doc_type: string;
      subject: string;
      criterion?: string;
      previous_feedback?: string[];
      version?: number;
      session_id?: number;
    }) => api.post<DraftReviewResult>("/api/coursework/review-draft", data),
    onError: () => {
      toast.error("Failed to review draft.");
    },
  });
}

export function useAnalyzeData() {
  return useMutation({
    mutationFn: (data: {
      data: string;
      subject: string;
      hypothesis: string;
      session_id?: number;
    }) => api.post<DataAnalysisResult>("/api/coursework/analyze-data", data),
    onError: () => {
      toast.error("Failed to analyze data.");
    },
  });
}

export function useToggleMilestone() {
  return useMutation({
    mutationFn: (data: {
      milestone_key: string;
      completed: boolean;
      subject?: string;
    }) => api.post("/api/lifecycle/milestone", {
      milestone_id: data.milestone_key,
      completed: data.completed,
      subject: data.subject,
    }),
    onError: () => {
      toast.error("Failed to update milestone.");
    },
  });
}
