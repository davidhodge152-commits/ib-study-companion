"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNav } from "@/components/layout/MobileNav";
import { MobileHeader } from "@/components/layout/MobileHeader";
import { UpgradeModal } from "@/components/shared/UpgradeModal";
import { CommandPalette } from "@/components/shared/CommandPalette";
import { isPublicRoute } from "@/lib/auth";

/** Pages that render full-width without sidebar (auth, onboarding) */
const FULL_WIDTH_ROUTES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/onboarding",
  "/try",
];

function isFullWidth(pathname: string): boolean {
  return FULL_WIDTH_ROUTES.some(
    (r) => pathname === r || pathname.startsWith(`${r}/`)
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const fullWidth = isFullWidth(pathname);

  if (fullWidth) {
    return (
      <main className="flex min-h-screen flex-col">
        {children}
        <UpgradeModal />
      </main>
    );
  }

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <MobileHeader />
      <main className="flex-1 overflow-y-auto pb-20 lg:ml-64 lg:pb-0">
        {/* Guest banner */}
        <div className="mx-auto max-w-6xl px-4 py-8 pt-16 sm:px-8 lg:pt-8">
          {children}
        </div>
      </main>
      <MobileNav />
      <UpgradeModal />
      <CommandPalette />
    </div>
  );
}
