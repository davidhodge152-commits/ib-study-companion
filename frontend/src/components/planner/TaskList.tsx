"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { usePlannerTasks, useToggleTask } from "@/lib/hooks/usePlanner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { CheckCircle2, Circle, Play, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PlannerTask } from "@/lib/types";

const priorityColors: Record<string, string> = {
  high: "bg-destructive/10 text-destructive border-destructive/20",
  medium: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  low: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20",
};

export function TaskList() {
  const { data, isLoading } = usePlannerTasks();
  const toggleTask = useToggleTask();
  const router = useRouter();
  const [showCompleted, setShowCompleted] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="h-5 w-5 rounded-full" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const tasks = data?.tasks ?? [];
  const today = new Date().toISOString().split("T")[0];
  const todayTasks = tasks.filter((t) => {
    const dueDate = t.due_date?.split("T")[0];
    return dueDate === today || dueDate === undefined;
  });
  const pendingTasks = todayTasks.filter((t) => !t.completed);
  const completedTasks = todayTasks.filter((t) => t.completed);

  if (tasks.length === 0) {
    return (
      <EmptyState
        title="No tasks for today"
        description="Generate a study plan to get personalized tasks."
      />
    );
  }

  const renderTask = (task: PlannerTask) => (
    <div
      key={task.id}
      className="flex items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-accent/50"
    >
      <button
        onClick={() =>
          toggleTask.mutate({ id: task.id, completed: !task.completed })
        }
        className="mt-0.5 shrink-0"
        aria-label={
          task.completed ? "Mark incomplete" : "Mark complete"
        }
      >
        {task.completed ? (
          <CheckCircle2 className="h-5 w-5 text-primary" />
        ) : (
          <Circle className="h-5 w-5 text-muted-foreground" />
        )}
      </button>
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm font-medium",
            task.completed && "line-through text-muted-foreground"
          )}
        >
          {task.title}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          {task.subject && (
            <Badge variant="outline" className="text-xs">
              {task.subject}
            </Badge>
          )}
          <Badge
            variant="outline"
            className={cn("text-xs", priorityColors[task.priority])}
          >
            {task.priority}
          </Badge>
        </div>
      </div>
      {!task.completed && (
        <Button
          size="icon-xs"
          variant="ghost"
          onClick={() =>
            router.push(
              `/study?subject=${encodeURIComponent(task.subject ?? task.title)}`
            )
          }
          aria-label="Start study session"
        >
          <Play className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );

  return (
    <div className="space-y-3">
      {pendingTasks.length > 0 ? (
        pendingTasks.map(renderTask)
      ) : (
        <p className="py-4 text-center text-sm text-muted-foreground">
          All tasks for today are done!
        </p>
      )}

      {completedTasks.length > 0 && (
        <>
          <button
            onClick={() => setShowCompleted(!showCompleted)}
            className="flex w-full items-center gap-2 text-xs font-medium text-muted-foreground"
          >
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 transition-transform",
                showCompleted && "rotate-180"
              )}
            />
            {completedTasks.length} completed
          </button>
          {showCompleted && completedTasks.map(renderTask)}
        </>
      )}
    </div>
  );
}
