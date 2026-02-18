"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api-client";
import { useStudyStore } from "../stores/study-store";
import type { StudyQuestion, GradeResult } from "../types";

export function useStudy() {
  const store = useStudyStore();

  const generateQuestion = useMutation({
    mutationFn: async ({
      subject,
      topic,
    }: {
      subject: string;
      topic: string;
    }) => {
      store.setIsGenerating(true);
      store.resetStreamContent();
      try {
        const stream = await api.stream("/api/study/generate", {
          subject,
          topic,
        });
        const reader = stream.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });

          // Parse SSE data lines
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") continue;
              try {
                const parsed = JSON.parse(data);
                if (parsed.content) {
                  fullText += parsed.content;
                  store.appendStreamContent(parsed.content);
                }
                if (parsed.question) {
                  store.setCurrentQuestion(parsed.question as StudyQuestion);
                }
              } catch {
                // partial JSON, append as text
                fullText += data;
                store.appendStreamContent(data);
              }
            }
          }
        }
        return fullText;
      } finally {
        store.setIsGenerating(false);
      }
    },
  });

  const gradeAnswer = useMutation({
    mutationFn: async ({
      questionId,
      answer,
    }: {
      questionId: string;
      answer: string;
    }) => {
      store.setIsGrading(true);
      try {
        return await api.post<GradeResult>("/api/study/grade", {
          question_id: questionId,
          answer,
        });
      } finally {
        store.setIsGrading(false);
      }
    },
    onSuccess: (result) => {
      store.setGradeResult(result);
    },
  });

  return {
    ...store,
    generateQuestion: generateQuestion.mutateAsync,
    gradeAnswer: gradeAnswer.mutateAsync,
    isGenerating: generateQuestion.isPending || store.isGenerating,
    isGrading: gradeAnswer.isPending || store.isGrading,
  };
}

export function useSubjects() {
  return useQuery({
    queryKey: ["subjects"],
    queryFn: () => api.get<{ subjects: string[] }>("/api/subjects"),
    staleTime: 10 * 60 * 1000,
  });
}

export function useTopics(subject: string) {
  return useQuery({
    queryKey: ["topics", subject],
    queryFn: () =>
      api.get<{ topics: string[] }>(`/api/subjects/${encodeURIComponent(subject)}/topics`),
    enabled: !!subject,
    staleTime: 10 * 60 * 1000,
  });
}
