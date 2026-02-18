"use client";

import { create } from "zustand";
import type { User, UserProfile, Gamification } from "../types";

interface AuthState {
  user: User | null;
  profile: UserProfile | null;
  gamification: Gamification | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setProfile: (profile: UserProfile | null) => void;
  setGamification: (gam: Gamification | null) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  profile: null,
  gamification: null,
  isLoading: true,
  isAuthenticated: false,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setProfile: (profile) => set({ profile }),
  setGamification: (gamification) => set({ gamification }),
  setLoading: (isLoading) => set({ isLoading }),
  reset: () =>
    set({
      user: null,
      profile: null,
      gamification: null,
      isAuthenticated: false,
    }),
}));
