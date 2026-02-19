"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface ExamTimerProps {
  startTime: number;
  durationMinutes: number;
  onExpired: () => void;
  className?: string;
}

function formatTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function ExamTimer({
  startTime,
  durationMinutes,
  onExpired,
  className,
}: ExamTimerProps) {
  const [remaining, setRemaining] = useState(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    return Math.max(0, durationMinutes * 60 - elapsed);
  });

  useEffect(() => {
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const r = Math.max(0, durationMinutes * 60 - elapsed);
      setRemaining(r);
      if (r <= 0) {
        clearInterval(interval);
        onExpired();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime, durationMinutes, onExpired]);

  const totalSeconds = durationMinutes * 60;
  const pct = (remaining / totalSeconds) * 100;

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="flex-1">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">
            Time Remaining
          </span>
          <span
            className={cn(
              "font-mono text-lg font-bold tabular-nums",
              pct > 25
                ? "text-foreground"
                : pct > 10
                  ? "text-amber-500"
                  : "text-destructive animate-pulse"
            )}
          >
            {formatTime(remaining)}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-1000",
              pct > 25
                ? "bg-primary"
                : pct > 10
                  ? "bg-amber-500"
                  : "bg-destructive"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
