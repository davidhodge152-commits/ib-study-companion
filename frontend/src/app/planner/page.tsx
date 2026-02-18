"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

const priorityColors: Record<string, string> = {
  high: "bg-destructive/10 text-destructive",
  medium: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400",
  low: "bg-green-500/10 text-green-700 dark:text-green-400",
};

const priorityBadgeVariant: Record<string, string> = {
  high: "bg-destructive/10 text-destructive border-destructive/20",
  medium:
    "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20",
  low: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20",
};

/** Inline chevron-down SVG icon */
function ChevronDown({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}

/** Inline play/start SVG icon */
function PlayIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

/** Inline calendar SVG icon */
function CalendarIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
      />
    </svg>
  );
}

/** Inline book/subject SVG icon */
function BookIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
      />
    </svg>
  );
}

export default function PlannerPage() {
  const { data, isLoading, error } = usePlannerTasks();
  const toggleTask = useToggleTask();
  const generatePlan = useGenerateStudyPlan();
  const router = useRouter();
  const [expandedTasks, setExpandedTasks] = useState<Set<number>>(new Set());

  const toggleExpanded = (taskId: number) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

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
                  {pendingTasks.map((task) => {
                    const isExpanded = expandedTasks.has(task.id);

                    return (
                      <li
                        key={task.id}
                        className="py-3 first:pt-0 last:pb-0"
                      >
                        {/* Top row: checkbox, title, priority, chevron */}
                        <div className="flex items-start gap-3">
                          {/* Checkbox */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleTask.mutate({
                                id: task.id,
                                completed: true,
                              });
                            }}
                            className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 border-primary transition-colors hover:bg-primary/10"
                            aria-label={`Mark "${task.title}" as complete`}
                          >
                            <span className="sr-only">Complete</span>
                          </button>

                          {/* Clickable expand area */}
                          <button
                            type="button"
                            onClick={() => toggleExpanded(task.id)}
                            className="flex flex-1 items-start justify-between text-left"
                            aria-expanded={isExpanded}
                            aria-label={`${isExpanded ? "Collapse" : "Expand"} task: ${task.title}`}
                          >
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium">
                                  {task.title}
                                </p>
                                <span
                                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${priorityColors[task.priority] ?? ""}`}
                                >
                                  {task.priority}
                                </span>
                              </div>
                              {!isExpanded && (
                                <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
                                  {task.description}
                                </p>
                              )}
                              {!isExpanded && (
                                <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                                  {task.subject && <span>{task.subject}</span>}
                                  <span>
                                    Due:{" "}
                                    {new Date(
                                      task.due_date
                                    ).toLocaleDateString()}
                                  </span>
                                </div>
                              )}
                            </div>

                            {/* Chevron indicator */}
                            <ChevronDown
                              className={`ml-2 mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${
                                isExpanded ? "rotate-180" : ""
                              }`}
                            />
                          </button>
                        </div>

                        {/* Expanded details panel */}
                        {isExpanded && (
                          <div className="ml-8 mt-3 space-y-3">
                            <Separator />

                            {/* Full description */}
                            <p className="text-sm text-foreground/80">
                              {task.description}
                            </p>

                            {/* Meta details */}
                            <div className="flex flex-wrap items-center gap-3">
                              {task.subject && (
                                <Badge
                                  variant="outline"
                                  className="gap-1.5 font-normal"
                                >
                                  <BookIcon className="h-3 w-3" />
                                  {task.subject}
                                </Badge>
                              )}
                              <Badge
                                variant="outline"
                                className="gap-1.5 font-normal"
                              >
                                <CalendarIcon className="h-3 w-3" />
                                Due:{" "}
                                {new Date(
                                  task.due_date
                                ).toLocaleDateString(undefined, {
                                  weekday: "short",
                                  year: "numeric",
                                  month: "short",
                                  day: "numeric",
                                })}
                              </Badge>
                              <Badge
                                variant="outline"
                                className={`gap-1.5 font-normal ${priorityBadgeVariant[task.priority] ?? ""}`}
                              >
                                Priority: {task.priority}
                              </Badge>
                            </div>

                            {/* Actions */}
                            <div className="flex items-center gap-2 pt-1">
                              <Button
                                size="sm"
                                onClick={() => {
                                  const subject =
                                    task.subject ??
                                    encodeURIComponent(task.title);
                                  router.push(
                                    `/study?subject=${encodeURIComponent(subject)}`
                                  );
                                }}
                                className="gap-1.5"
                              >
                                <PlayIcon className="h-4 w-4" />
                                Start Session
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  toggleTask.mutate({
                                    id: task.id,
                                    completed: true,
                                  })
                                }
                              >
                                Mark Complete
                              </Button>
                            </div>
                          </div>
                        )}
                      </li>
                    );
                  })}
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
                  {completedTasks.map((task) => {
                    const isExpanded = expandedTasks.has(task.id);

                    return (
                      <li
                        key={task.id}
                        className="py-3 first:pt-0 last:pb-0"
                      >
                        {/* Top row: checkbox, title, chevron */}
                        <div className="flex items-start gap-3">
                          {/* Completed checkbox */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleTask.mutate({
                                id: task.id,
                                completed: false,
                              });
                            }}
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

                          {/* Clickable expand area */}
                          <button
                            type="button"
                            onClick={() => toggleExpanded(task.id)}
                            className="flex flex-1 items-start justify-between text-left"
                            aria-expanded={isExpanded}
                            aria-label={`${isExpanded ? "Collapse" : "Expand"} task: ${task.title}`}
                          >
                            <div className="flex-1">
                              <p className="text-sm font-medium text-muted-foreground line-through">
                                {task.title}
                              </p>
                              {!isExpanded && task.subject && (
                                <span className="text-xs text-muted-foreground">
                                  {task.subject}
                                </span>
                              )}
                            </div>

                            {/* Chevron indicator */}
                            <ChevronDown
                              className={`ml-2 mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${
                                isExpanded ? "rotate-180" : ""
                              }`}
                            />
                          </button>
                        </div>

                        {/* Expanded details panel */}
                        {isExpanded && (
                          <div className="ml-8 mt-3 space-y-3">
                            <Separator />

                            <p className="text-sm text-muted-foreground">
                              {task.description}
                            </p>

                            <div className="flex flex-wrap items-center gap-3">
                              {task.subject && (
                                <Badge
                                  variant="outline"
                                  className="gap-1.5 font-normal"
                                >
                                  <BookIcon className="h-3 w-3" />
                                  {task.subject}
                                </Badge>
                              )}
                              <Badge
                                variant="outline"
                                className="gap-1.5 font-normal"
                              >
                                <CalendarIcon className="h-3 w-3" />
                                Due:{" "}
                                {new Date(
                                  task.due_date
                                ).toLocaleDateString(undefined, {
                                  weekday: "short",
                                  year: "numeric",
                                  month: "short",
                                  day: "numeric",
                                })}
                              </Badge>
                              <Badge
                                variant="outline"
                                className={`gap-1.5 font-normal ${priorityBadgeVariant[task.priority] ?? ""}`}
                              >
                                Priority: {task.priority}
                              </Badge>
                            </div>

                            {/* Actions */}
                            <div className="flex items-center gap-2 pt-1">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  toggleTask.mutate({
                                    id: task.id,
                                    completed: false,
                                  })
                                }
                              >
                                Mark Incomplete
                              </Button>
                            </div>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
