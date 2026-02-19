"use client";

import { cn } from "@/lib/utils";

interface IAWordCounterProps {
  text: string;
  limit?: number;
}

export function IAWordCounter({ text, limit = 4000 }: IAWordCounterProps) {
  const wordCount = text.trim()
    ? text.trim().split(/\s+/).length
    : 0;

  const pct = (wordCount / limit) * 100;

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "text-sm font-medium tabular-nums",
          pct < 80
            ? "text-green-600 dark:text-green-400"
            : pct <= 100
              ? "text-amber-600 dark:text-amber-400"
              : "text-destructive"
        )}
      >
        {wordCount.toLocaleString()}
      </span>
      <span className="text-sm text-muted-foreground">
        / {limit.toLocaleString()} words
      </span>
    </div>
  );
}
