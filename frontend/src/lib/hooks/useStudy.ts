"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api-client";
import { useStudyStore } from "../stores/study-store";
import type { StudyQuestion, GradeResult, GenerateResponse } from "../types";

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
        const data = await api.post<GenerateResponse>("/api/study/generate", {
          subject,
          topic,
        });

        // Set the first question from the response
        if (data.questions && data.questions.length > 0) {
          const q = data.questions[0];
          const question: StudyQuestion = {
            id: `q-${Date.now()}`,
            subject,
            topic: q.topic || topic,
            level: "HL",
            question_text: q.question_text,
            question: q.question_text,
            marks: q.marks || 0,
            command_term: q.command_term,
            model_answer: q.model_answer,
          };
          store.setCurrentQuestion(question);
          store.appendStreamContent(q.question_text);
        }
        return data;
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
