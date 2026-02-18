import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StudyStreakProps {
  streak: number;
  weekData?: boolean[];
  className?: string;
}

const DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"];

export function StudyStreak({ streak, weekData, className }: StudyStreakProps) {
  // Default to 7 false values if weekData is not provided
  const days = weekData ?? Array(7).fill(false) as boolean[];

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span
            className={cn(
              "text-2xl",
              streak > 0 ? "animate-pulse" : "opacity-40"
            )}
            role="img"
            aria-label="fire"
          >
            🔥
          </span>
          Study Streak
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-bold tracking-tight">{streak}</span>
          <span className="text-sm text-muted-foreground">
            day{streak !== 1 ? "s" : ""}
          </span>
        </div>

        <p className="mt-1 text-xs text-muted-foreground">
          {streak > 0
            ? "Keep it up! Study today to maintain your streak."
            : "Start studying to begin your streak!"}
        </p>

        {/* 7-day heatmap */}
        <div className="mt-4 flex items-center gap-1.5">
          {days.map((active, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "h-8 w-8 rounded-md transition-colors",
                  active
                    ? "bg-emerald-500 dark:bg-emerald-400"
                    : "bg-muted"
                )}
                title={active ? "Active" : "Inactive"}
              />
              <span className="text-[10px] text-muted-foreground">
                {DAY_LABELS[i]}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
