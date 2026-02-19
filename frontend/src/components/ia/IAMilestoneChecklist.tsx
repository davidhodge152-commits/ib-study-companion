"use client";

import { useState } from "react";
import { useToggleMilestone } from "@/lib/hooks/useIA";
import { CheckCircle2, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Milestone {
  key: string;
  label: string;
}

const IA_MILESTONES: Milestone[] = [
  { key: "topic_approved", label: "Topic approved" },
  { key: "research_completed", label: "Research completed" },
  { key: "data_collected", label: "Data collected" },
  { key: "first_draft", label: "First draft submitted" },
  { key: "teacher_feedback", label: "Teacher feedback received" },
  { key: "revision_complete", label: "Revision complete" },
  { key: "final_submission", label: "Final submission" },
];

interface IAMilestoneChecklistProps {
  subject: string;
  initialCompleted?: string[];
}

export function IAMilestoneChecklist({
  subject,
  initialCompleted = [],
}: IAMilestoneChecklistProps) {
  const [completed, setCompleted] = useState<Set<string>>(
    new Set(initialCompleted)
  );
  const toggleMilestone = useToggleMilestone();

  const handleToggle = (key: string) => {
    const isCompleted = completed.has(key);
    const newCompleted = new Set(completed);
    if (isCompleted) {
      newCompleted.delete(key);
    } else {
      newCompleted.add(key);
    }
    setCompleted(newCompleted);
    toggleMilestone.mutate({
      milestone_key: key,
      completed: !isCompleted,
      subject,
    });
  };

  return (
    <div className="space-y-1">
      <p className="mb-3 text-sm text-muted-foreground">
        Track your IA progress through key milestones.
      </p>
      {IA_MILESTONES.map((m) => {
        const isCompleted = completed.has(m.key);
        return (
          <button
            key={m.key}
            onClick={() => handleToggle(m.key)}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent"
          >
            {isCompleted ? (
              <CheckCircle2 className="h-5 w-5 text-primary" />
            ) : (
              <Circle className="h-5 w-5 text-muted-foreground" />
            )}
            <span
              className={cn(
                "text-sm font-medium",
                isCompleted && "text-muted-foreground line-through"
              )}
            >
              {m.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
