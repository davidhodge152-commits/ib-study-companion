"use client";

import { useIAStore } from "@/lib/stores/ia-store";
import { useCourseworkSession } from "@/lib/hooks/useIA";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { IADraftEditor } from "./IADraftEditor";
import { IAFeedbackPanel } from "./IAFeedbackPanel";
import { IAFeasibilityCheck } from "./IAFeasibilityCheck";
import { IADataAnalysis } from "./IADataAnalysis";
import { IAMilestoneChecklist } from "./IAMilestoneChecklist";
import { IACriteriaGuide } from "./IACriteriaGuide";
import { IAWordCounter } from "./IAWordCounter";
import { SCIENCE_SUBJECTS } from "@/lib/types/ia";
import { ArrowLeft } from "lucide-react";

interface IAEditorProps {
  sessionId: number;
  onBack: () => void;
}

const phaseLabels: Record<string, string> = {
  proposal: "Proposal",
  research: "Research",
  drafting: "Drafting",
  revision: "Revision",
  final: "Final",
};

export function IAEditor({ sessionId, onBack }: IAEditorProps) {
  const { activeTab, setActiveTab, draftText } = useIAStore();
  const { data, isLoading } = useCourseworkSession(sessionId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  const session = data?.session;
  if (!session) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">Session not found.</p>
        <Button variant="outline" className="mt-4" onClick={onBack}>
          Go Back
        </Button>
      </div>
    );
  }

  const isScience = SCIENCE_SUBJECTS.includes(session.subject);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon-sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h2 className="text-lg font-semibold">
              {session.title || "Untitled IA"}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline">{session.subject}</Badge>
              <Badge variant="secondary">
                {phaseLabels[session.current_phase] ?? session.current_phase}
              </Badge>
              <IAWordCounter text={draftText} />
            </div>
          </div>
        </div>
      </div>

      {/* Criteria guide */}
      <IACriteriaGuide subject={session.subject} />

      {/* Workspace tabs */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as typeof activeTab)}
      >
        <TabsList>
          <TabsTrigger value="editor">Editor</TabsTrigger>
          <TabsTrigger value="review">AI Review</TabsTrigger>
          {isScience && <TabsTrigger value="data">Data</TabsTrigger>}
          <TabsTrigger value="milestones">Milestones</TabsTrigger>
        </TabsList>

        <TabsContent value="editor" className="mt-4">
          {session.current_phase === "proposal" ? (
            <IAFeasibilityCheck
              subject={session.subject}
              docType={session.doc_type}
            />
          ) : (
            <IADraftEditor
              subject={session.subject}
              docType={session.doc_type}
              sessionId={sessionId}
            />
          )}
        </TabsContent>

        <TabsContent value="review" className="mt-4">
          <IAFeedbackPanel />
        </TabsContent>

        {isScience && (
          <TabsContent value="data" className="mt-4">
            <IADataAnalysis
              subject={session.subject}
              sessionId={sessionId}
            />
          </TabsContent>
        )}

        <TabsContent value="milestones" className="mt-4">
          <IAMilestoneChecklist subject={session.subject} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
