"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../api-client";
import type {
  ExamGenerateResponse,
  ExamSubmitResponse,
  ExamResultsResponse,
  ExamHistoryResponse,
} from "../types/exam";

export function useExamGenerate() {
  return useMutation({
    mutationFn: (params: {
      subject: string;
      level: string;
      paper_number: number;
    }) => api.post<ExamGenerateResponse>("/api/exam/generate", params),
    onError: () => {
      toast.error("Failed to generate exam paper. Please try again.");
    },
  });
}

export function useExamSubmit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      ...data
    }: {
      sessionId: number;
      answers: { question_number: number; answer: string }[];
      earned_marks: number;
      total_marks: number;
      subject: string;
      level: string;
    }) => api.post<ExamSubmitResponse>(`/api/exam/${sessionId}/submit`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["exam", "history"] });
    },
    onError: () => {
      toast.error("Failed to submit exam. Please try again.");
    },
  });
}

export function useExamResults(sessionId: number | null) {
  return useQuery({
    queryKey: ["exam", "results", sessionId],
    queryFn: () =>
      api.get<ExamResultsResponse>(`/api/exam/${sessionId}/results`),
    enabled: !!sessionId,
    staleTime: Infinity,
  });
}

export function useExamHistory() {
  return useQuery({
    queryKey: ["exam", "history"],
    queryFn: () => api.get<ExamHistoryResponse>("/api/exam/history"),
    staleTime: 2 * 60 * 1000,
  });
}
