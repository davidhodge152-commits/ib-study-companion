"use client";

import { create } from "zustand";
import type { StudyQuestion, GradeResult } from "../types";

interface StudyState {
  currentQuestion: StudyQuestion | null;
  answer: string;
  gradeResult: GradeResult | null;
  isGenerating: boolean;
  isGrading: boolean;
  streamedContent: string;
  selectedSubject: string;
  selectedTopic: string;
  setCurrentQuestion: (q: StudyQuestion | null) => void;
  setAnswer: (a: string) => void;
  setGradeResult: (r: GradeResult | null) => void;
  setIsGenerating: (g: boolean) => void;
  setIsGrading: (g: boolean) => void;
  appendStreamContent: (chunk: string) => void;
  resetStreamContent: () => void;
  setSelectedSubject: (s: string) => void;
  setSelectedTopic: (t: string) => void;
  reset: () => void;
}

export const useStudyStore = create<StudyState>((set) => ({
  currentQuestion: null,
  answer: "",
  gradeResult: null,
  isGenerating: false,
  isGrading: false,
  streamedContent: "",
  selectedSubject: "",
  selectedTopic: "",
  setCurrentQuestion: (currentQuestion) =>
    set({ currentQuestion, gradeResult: null, answer: "" }),
  setAnswer: (answer) => set({ answer }),
  setGradeResult: (gradeResult) => set({ gradeResult }),
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  setIsGrading: (isGrading) => set({ isGrading }),
  appendStreamContent: (chunk) =>
    set((state) => ({ streamedContent: state.streamedContent + chunk })),
  resetStreamContent: () => set({ streamedContent: "" }),
  setSelectedSubject: (selectedSubject) =>
    set({ selectedSubject, selectedTopic: "" }),
  setSelectedTopic: (selectedTopic) => set({ selectedTopic }),
  reset: () =>
    set({
      currentQuestion: null,
      answer: "",
      gradeResult: null,
      isGenerating: false,
      isGrading: false,
      streamedContent: "",
    }),
}));
