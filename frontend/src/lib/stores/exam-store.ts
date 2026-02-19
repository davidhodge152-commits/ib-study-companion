"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ExamPaper, ExamPhase } from "../types/exam";

interface ExamState {
  // Session state
  sessionId: number | null;
  paper: ExamPaper | null;
  phase: ExamPhase;
  answers: Record<number, string>;
  currentQuestionIndex: number;

  // Timer state (Date.now() based to prevent drift)
  examStartTime: number | null;
  readingStartTime: number | null;

  // Actions
  setPaper: (sessionId: number, paper: ExamPaper) => void;
  setPhase: (phase: ExamPhase) => void;
  setAnswer: (questionNumber: number, answer: string) => void;
  setCurrentQuestionIndex: (index: number) => void;
  startReading: () => void;
  startExam: () => void;
  reset: () => void;
}

export const useExamStore = create<ExamState>()(
  persist(
    (set) => ({
      sessionId: null,
      paper: null,
      phase: "config",
      answers: {},
      currentQuestionIndex: 0,
      examStartTime: null,
      readingStartTime: null,

      setPaper: (sessionId, paper) =>
        set({
          sessionId,
          paper,
          answers: {},
          currentQuestionIndex: 0,
          phase: "reading",
        }),

      setPhase: (phase) => set({ phase }),

      setAnswer: (questionNumber, answer) =>
        set((state) => ({
          answers: { ...state.answers, [questionNumber]: answer },
        })),

      setCurrentQuestionIndex: (currentQuestionIndex) =>
        set({ currentQuestionIndex }),

      startReading: () =>
        set({ phase: "reading", readingStartTime: Date.now() }),

      startExam: () =>
        set({ phase: "active", examStartTime: Date.now() }),

      reset: () =>
        set({
          sessionId: null,
          paper: null,
          phase: "config",
          answers: {},
          currentQuestionIndex: 0,
          examStartTime: null,
          readingStartTime: null,
        }),
    }),
    {
      name: "exam-session",
      partialize: (state) => ({
        sessionId: state.sessionId,
        paper: state.paper,
        phase: state.phase,
        answers: state.answers,
        currentQuestionIndex: state.currentQuestionIndex,
        examStartTime: state.examStartTime,
        readingStartTime: state.readingStartTime,
      }),
    }
  )
);
