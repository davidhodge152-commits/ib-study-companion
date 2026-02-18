"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { isPublicRoute } from "@/lib/auth";
import { api } from "@/lib/api-client";
import { useUIStore } from "@/lib/stores/ui-store";

export function AuthProvider({ children }: { children: ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const showUpgradeModal = useUIStore((s) => s.showUpgradeModal);

  // Wire up API client callbacks — only redirect if not already on a public route
  useEffect(() => {
    api.setOnUnauthorized(() => {
      if (!isPublicRoute(pathname)) {
        router.push("/login");
      }
    });
    api.setOnUpgradeRequired((type, plan) => showUpgradeModal(type, plan));
  }, [router, pathname, showUpgradeModal]);

  // Redirect unauthenticated users away from protected routes
  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isPublicRoute(pathname)) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, pathname, router]);

  // Show skeleton layout while checking auth on protected routes
  // This renders the sidebar/shell shape so it doesn't feel like a blank page
  if (isLoading && !isPublicRoute(pathname)) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
