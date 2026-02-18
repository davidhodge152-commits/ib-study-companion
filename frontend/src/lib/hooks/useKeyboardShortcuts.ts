"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface ShortcutConfig {
  /** Whether shortcuts are active (disable on input focus) */
  enabled?: boolean;
}

/**
 * Global keyboard shortcuts for navigation.
 * Uses 'g' prefix for "go to" shortcuts (like GitHub):
 * - g then d → Dashboard
 * - g then s → Study
 * - g then t → Tutor
 * - g then f → Flashcards
 * - g then i → Insights
 * - g then p → Planner
 * - ? → Show shortcuts help
 */
export function useKeyboardShortcuts(config: ShortcutConfig = {}) {
  const { enabled = true } = config;
  const router = useRouter();

  useEffect(() => {
    if (!enabled) return;

    let gPending = false;
    let gTimeout: ReturnType<typeof setTimeout>;

    const handler = (e: KeyboardEvent) => {
      // Skip if user is typing in an input, textarea, or contenteditable
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }

      // Skip if modifier keys are held (except for Cmd+K which is handled elsewhere)
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key.toLowerCase();

      if (gPending) {
        gPending = false;
        clearTimeout(gTimeout);
        e.preventDefault();

        const routes: Record<string, string> = {
          d: "/dashboard",
          s: "/study",
          t: "/tutor",
          f: "/flashcards",
          i: "/insights",
          p: "/planner",
          c: "/community",
          a: "/admissions",
          g: "/groups",
        };

        if (routes[key]) {
          router.push(routes[key]);
        }
        return;
      }

      if (key === "g") {
        gPending = true;
        gTimeout = setTimeout(() => {
          gPending = false;
        }, 800);
        return;
      }

      // '?' to show keyboard shortcuts (dispatch event for command palette)
      if (key === "?" || (e.shiftKey && key === "/")) {
        // Could open a shortcuts dialog in the future
        return;
      }
    };

    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      clearTimeout(gTimeout);
    };
  }, [enabled, router]);
}
