"use client";

import { useState } from "react";
import {
  useDeadlines,
  useCreateDeadline,
  useUpdateDeadline,
} from "@/lib/hooks/useAdaptivePlanner";
import { useSubjects } from "@/lib/hooks/useStudy";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { CheckCircle2, Circle, Calendar, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

const importanceColors: Record<string, string> = {
  high: "bg-destructive/10 text-destructive border-destructive/20",
  medium: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  low: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20",
};

export function DeadlineManager() {
  const { data, isLoading } = useDeadlines();
  const createDeadline = useCreateDeadline();
  const updateDeadline = useUpdateDeadline();
  const { data: subjectsData } = useSubjects();
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [importance, setImportance] = useState("medium");

  const subjects = subjectsData?.subjects ?? [];

  const handleCreate = () => {
    if (!title || !dueDate) return;
    createDeadline.mutate(
      {
        title,
        subject,
        deadline_type: "exam",
        due_date: dueDate,
        importance,
      },
      {
        onSuccess: () => {
          setTitle("");
          setSubject("");
          setDueDate("");
          setImportance("medium");
          setShowForm(false);
        },
      }
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  const deadlines = data?.deadlines ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {deadlines.length} deadline{deadlines.length !== 1 ? "s" : ""}
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowForm(!showForm)}
        >
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Add Deadline
        </Button>
      </div>

      {/* Inline add form */}
      {showForm && (
        <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
          <Input
            placeholder="Deadline title (e.g. Biology Paper 2)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-3">
            <Select value={subject} onValueChange={setSubject}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Subject" />
              </SelectTrigger>
              <SelectContent>
                {subjects.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-3">
            <Select value={importance} onValueChange={setImportance}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={handleCreate}
              disabled={!title || !dueDate || createDeadline.isPending}
              size="sm"
            >
              {createDeadline.isPending ? "Adding..." : "Add"}
            </Button>
          </div>
        </div>
      )}

      {/* Deadline list */}
      {deadlines.length === 0 && !showForm ? (
        <EmptyState
          icon={<Calendar className="h-6 w-6" />}
          title="No deadlines"
          description="Add your exam dates and assignment deadlines to get a more personalized study plan."
        />
      ) : (
        <div className="space-y-2">
          {deadlines.map((d) => {
            const daysUntil = Math.ceil(
              (new Date(d.due_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
            );
            return (
              <div
                key={d.id}
                className="flex items-center gap-3 rounded-lg border p-3"
              >
                <button
                  onClick={() =>
                    updateDeadline.mutate({
                      id: d.id,
                      completed: !d.completed,
                    })
                  }
                  className="shrink-0"
                >
                  {d.completed ? (
                    <CheckCircle2 className="h-5 w-5 text-primary" />
                  ) : (
                    <Circle className="h-5 w-5 text-muted-foreground" />
                  )}
                </button>
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "text-sm font-medium",
                      d.completed && "line-through text-muted-foreground"
                    )}
                  >
                    {d.title}
                  </p>
                  <div className="mt-1 flex items-center gap-2">
                    {d.subject && (
                      <Badge variant="outline" className="text-xs">
                        {d.subject}
                      </Badge>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {new Date(d.due_date).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs",
                      importanceColors[d.importance]
                    )}
                  >
                    {d.importance}
                  </Badge>
                  {!d.completed && (
                    <span
                      className={cn(
                        "text-xs font-medium",
                        daysUntil <= 3
                          ? "text-destructive"
                          : daysUntil <= 7
                            ? "text-amber-600 dark:text-amber-400"
                            : "text-muted-foreground"
                      )}
                    >
                      {daysUntil <= 0
                        ? "Overdue"
                        : `${daysUntil}d`}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
