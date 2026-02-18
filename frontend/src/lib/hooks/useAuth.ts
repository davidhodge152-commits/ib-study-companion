"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuthStore } from "../stores/auth-store";
import * as authLib from "../auth";
import type { User, UserProfile, Gamification } from "../types";

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setUser, setProfile, setGamification, setLoading, reset } =
    useAuthStore();

  const userQuery = useQuery({
    queryKey: ["auth", "user"],
    queryFn: authLib.getCurrentUser,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const profileQuery = useQuery({
    queryKey: ["auth", "profile"],
    queryFn: authLib.getUserProfile,
    enabled: !!userQuery.data,
    staleTime: 5 * 60 * 1000,
  });

  const gamQuery = useQuery({
    queryKey: ["auth", "gamification"],
    queryFn: authLib.getGamification,
    enabled: !!userQuery.data,
    staleTime: 60 * 1000,
  });

  // Sync to store
  if (userQuery.data !== undefined) {
    setUser(userQuery.data);
  }
  if (profileQuery.data !== undefined) {
    setProfile(profileQuery.data);
  }
  if (gamQuery.data !== undefined) {
    setGamification(gamQuery.data);
  }
  if (!userQuery.isLoading) {
    setLoading(false);
  }

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authLib.login(email, password),
    onSuccess: (result) => {
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ["auth"] });
        router.push("/dashboard");
      }
    },
  });

  const registerMutation = useMutation({
    mutationFn: authLib.register,
    onSuccess: (result) => {
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ["auth"] });
        router.push("/onboarding");
      }
    },
  });

  const logoutMutation = useMutation({
    mutationFn: authLib.logout,
    onSuccess: () => {
      reset();
      queryClient.clear();
      router.push("/login");
    },
  });

  return {
    user: userQuery.data as User | null,
    profile: profileQuery.data as UserProfile | null,
    gamification: gamQuery.data as Gamification | null,
    isLoading: userQuery.isLoading,
    isAuthenticated: !!userQuery.data,
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
    loginError: loginMutation.data?.error,
    registerError: registerMutation.data?.error,
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
  };
}
