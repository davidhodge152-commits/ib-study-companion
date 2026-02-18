"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, BookOpen, Layers, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

const MOBILE_ITEMS = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/study", label: "Study", icon: BookOpen },
  { href: "/flashcards", label: "Cards", icon: Layers },
  { href: "/insights", label: "Insights", icon: BarChart3 },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-20 flex justify-around border-t border-slate-200 bg-white py-1 px-1 dark:border-slate-700 dark:bg-slate-800 lg:hidden safe-area-bottom"
      role="navigation"
      aria-label="Mobile navigation"
    >
      {MOBILE_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex min-h-[56px] min-w-[56px] flex-col items-center justify-center gap-0.5 px-2 py-1 relative",
              active
                ? "text-brand-600 dark:text-brand-400"
                : "text-slate-500"
            )}
            aria-current={active ? "page" : undefined}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
            <span className="text-[10px] font-medium">{label}</span>
            {active && (
              <span className="absolute bottom-1 h-0.5 w-5 rounded-full bg-brand-600 dark:bg-brand-400" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}
