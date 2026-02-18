"use client";

import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  upgradeModal: {
    open: boolean;
    type: "credits" | "plan";
    planName?: string;
  };
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  showUpgradeModal: (type: "credits" | "plan", planName?: string) => void;
  hideUpgradeModal: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  upgradeModal: { open: false, type: "credits" },
  toggleSidebar: () =>
    set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  showUpgradeModal: (type, planName) =>
    set({ upgradeModal: { open: true, type, planName } }),
  hideUpgradeModal: () =>
    set((state) => ({
      upgradeModal: { ...state.upgradeModal, open: false },
    })),
}));
