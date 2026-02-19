"use client";

import { create } from "zustand";
import type { IAPhase } from "../types/ia";

interface IAState {
  activeSessionId: number | null;
  activeTab: "editor" | "review" | "data" | "milestones";
  draftText: string;
  previousFeedback: string[];

  setActiveSessionId: (id: number | null) => void;
  setActiveTab: (tab: IAState["activeTab"]) => void;
  setDraftText: (text: string) => void;
  addFeedback: (feedback: string) => void;
  clearFeedback: () => void;
  reset: () => void;
}

export const useIAStore = create<IAState>((set) => ({
  activeSessionId: null,
  activeTab: "editor",
  draftText: "",
  previousFeedback: [],

  setActiveSessionId: (activeSessionId) =>
    set({ activeSessionId, draftText: "", previousFeedback: [], activeTab: "editor" }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setDraftText: (draftText) => set({ draftText }),
  addFeedback: (feedback) =>
    set((state) => ({
      previousFeedback: [...state.previousFeedback, feedback],
    })),
  clearFeedback: () => set({ previousFeedback: [] }),
  reset: () =>
    set({
      activeSessionId: null,
      activeTab: "editor",
      draftText: "",
      previousFeedback: [],
    }),
}));
