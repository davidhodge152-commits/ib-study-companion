import { BookOpen, Target, Flame, CalendarCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatsCardsProps {
  stats: {
    total_questions: number;
    avg_grade: number;
    current_streak: number;
    upcoming_tasks: number;
  };
  className?: string;
}

const STAT_CONFIG = [
  {
    key: "total_questions" as const,
    label: "Questions Answered",
    icon: BookOpen,
    color: "text-blue-500",
    bg: "bg-blue-500/10",
    format: (v: number) => v.toLocaleString(),
  },
  {
    key: "avg_grade" as const,
    label: "Average Grade",
    icon: Target,
    color: "text-emerald-500",
    bg: "bg-emerald-500/10",
    format: (v: number) => `${Math.round(v)}%`,
  },
  {
    key: "current_streak" as const,
    label: "Current Streak",
    icon: Flame,
    color: "text-orange-500",
    bg: "bg-orange-500/10",
    format: (v: number) => `${v} day${v !== 1 ? "s" : ""}`,
  },
  {
    key: "upcoming_tasks" as const,
    label: "Upcoming Tasks",
    icon: CalendarCheck,
    color: "text-violet-500",
    bg: "bg-violet-500/10",
    format: (v: number) => v.toLocaleString(),
  },
];

export function StatsCards({ stats, className }: StatsCardsProps) {
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-4", className)}>
      {STAT_CONFIG.map(({ key, label, icon: Icon, color, bg, format }) => (
        <Card key={key} className="py-4">
          <CardContent className="flex items-center gap-4">
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                bg
              )}
            >
              <Icon className={cn("h-5 w-5", color)} />
            </div>
            <div className="min-w-0">
              <p className="text-sm text-muted-foreground">{label}</p>
              <p className="text-2xl font-bold tracking-tight">
                {format(stats[key])}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
