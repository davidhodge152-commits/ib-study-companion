"use client";

import {
  usePlannerTasks,
  useToggleTask,
  useGenerateStudyPlan,
} from "@/lib/hooks/usePlanner";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

const priorityColors: Record<string, string> = {
  high: "bg-destructive/10 text-destructive",
  medium: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400",
  low: "bg-green-500/10 text-green-700 dark:text-green-400",
};

export default function PlannerPage() {
  const { data, isLoading, error } = usePlannerTasks();
  const toggleTask = useToggleTask();
  const generatePlan = useGenerateStudyPlan();

  if (isLoading) return <LoadingSkeleton variant="list" count={6} />;

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
        <p className="text-destructive">
          Failed to load tasks. Please try refreshing.
        </p>
      </div>
    );
  }

  const tasks = data?.tasks ?? [];
  const pendingTasks = tasks.filter((t) => !t.completed);
  const completedTasks = tasks.filter((t) => t.completed);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Study Planner</h1>
          <p className="text-muted-foreground">
            Organize your study schedule and track task completion
          </p>
        </div>
        <Button
          onClick={() => generatePlan.mutate()}
          disabled={generatePlan.isPending}
        >
          {generatePlan.isPending ? "Generating..." : "Generate Study Plan"}
        </Button>
      </div>

      {tasks.length === 0 ? (
        <EmptyState
          title="No tasks yet"
          description="Generate an AI-powered study plan based on your subjects and upcoming exams."
          action={
            <Button
              onClick={() => generatePlan.mutate()}
              disabled={generatePlan.isPending}
            >
              {generatePlan.isPending ? "Generating..." : "Generate Study Plan"}
            </Button>
          }
        />
      ) : (
        <div className="space-y-6">
          {/* Pending Tasks */}
          {pendingTasks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>To Do ({pendingTasks.length})</CardTitle>
                <CardDescription>
                  Tasks sorted by priority and due date
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="divide-y">
                  {pendingTasks.map((task) => (
                    <li
                      key={task.id}
                      className="flex items-start gap-3 py-3 first:pt-0 last:pb-0"
                    >
                      <button
                        type="button"
                        onClick={() =>
                          toggleTask.mutate({
                            id: task.id,
                            completed: true,
                          })
                        }
                        disabled={toggleTask.isPending}
                        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 border-primary transition-colors hover:bg-primary/10"
                        aria-label={`Mark "${task.title}" as complete`}
                      >
                        <span className="sr-only">Complete</span>
                      </button>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium">{task.title}</p>
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${priorityColors[task.priority] ?? ""}`}
                          >
                            {task.priority}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {task.description}
                        </p>
                        <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                          {task.subject && <span>{task.subject}</span>}
                          <span>
                            Due:{" "}
                            {new Date(task.due_date).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Completed Tasks */}
          {completedTasks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Completed ({completedTasks.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="divide-y">
                  {completedTasks.map((task) => (
                    <li
                      key={task.id}
                      className="flex items-start gap-3 py-3 first:pt-0 last:pb-0"
                    >
                      <button
                        type="button"
                        onClick={() =>
                          toggleTask.mutate({
                            id: task.id,
                            completed: false,
                          })
                        }
                        disabled={toggleTask.isPending}
                        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 border-muted-foreground bg-primary transition-colors"
                        aria-label={`Mark "${task.title}" as incomplete`}
                      >
                        <svg
                          className="h-3 w-3 text-primary-foreground"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={3}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M5 13l4 4L19 7"
                          />
                        </svg>
                      </button>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-muted-foreground line-through">
                          {task.title}
                        </p>
                        {task.subject && (
                          <span className="text-xs text-muted-foreground">
                            {task.subject}
                          </span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
