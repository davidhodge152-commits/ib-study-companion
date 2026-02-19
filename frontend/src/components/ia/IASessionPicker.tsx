"use client";

import { useState } from "react";
import { useCourseworkSessions } from "@/lib/hooks/useIA";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { IACreateDialog } from "./IACreateDialog";
import { FileEdit, Plus } from "lucide-react";

interface IASessionPickerProps {
  onSelectSession: (id: number) => void;
}

const phaseLabels: Record<string, string> = {
  proposal: "Proposal",
  research: "Research",
  drafting: "Drafting",
  revision: "Revision",
  final: "Final",
};

const phaseColors: Record<string, string> = {
  proposal: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
  research: "bg-purple-500/10 text-purple-700 dark:text-purple-400",
  drafting: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
  revision: "bg-green-500/10 text-green-700 dark:text-green-400",
  final: "bg-primary/10 text-primary",
};

export function IASessionPicker({ onSelectSession }: IASessionPickerProps) {
  const { data, isLoading } = useCourseworkSessions();
  const [showCreate, setShowCreate] = useState(false);

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
    );
  }

  const sessions = data?.sessions ?? [];

  return (
    <>
      {sessions.length === 0 ? (
        <EmptyState
          icon={<FileEdit className="h-6 w-6" />}
          title="No IA projects yet"
          description="Start your Internal Assessment with AI-powered feedback, criterion rubrics, and milestone tracking."
          action={
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New IA Project
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {sessions.length} project{sessions.length !== 1 ? "s" : ""}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCreate(true)}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              New IA
            </Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sessions.map((s) => (
              <Card
                key={s.id}
                className="cursor-pointer transition-colors hover:bg-accent/50"
                onClick={() => onSelectSession(s.id)}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-base line-clamp-1">
                    {s.title || "Untitled IA"}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{s.subject}</Badge>
                    <Badge
                      variant="secondary"
                      className={phaseColors[s.current_phase] ?? ""}
                    >
                      {phaseLabels[s.current_phase] ?? s.current_phase}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {new Date(s.created_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      <IACreateDialog
        open={showCreate}
        onOpenChange={setShowCreate}
        onCreated={onSelectSession}
      />
    </>
  );
}
