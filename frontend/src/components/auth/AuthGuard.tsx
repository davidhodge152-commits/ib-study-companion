"use client";

import { useAuth } from "@/lib/hooks/useAuth";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return <LoadingSkeleton variant="page" />;
  }

  if (!isAuthenticated) {
    return null; // AuthProvider handles redirect
  }

  return <>{children}</>;
}
