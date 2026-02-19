"use client";

import { useCallback, useState } from "react";
import { useIAStore } from "@/lib/stores/ia-store";
import { useReviewDraft } from "@/lib/hooks/useIA";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { IAWordCounter } from "./IAWordCounter";
import { Send } from "lucide-react";
import {
  SCIENCE_SUBJECTS,
  SCIENCE_IA_CRITERIA,
  DEFAULT_IA_CRITERIA,
  type IACriterion,
} from "@/lib/types/ia";

interface IADraftEditorProps {
  subject: string;
  docType: string;
  sessionId: number;
}

export function IADraftEditor({
  subject,
  docType,
  sessionId,
}: IADraftEditorProps) {
  const { draftText, setDraftText, previousFeedback, addFeedback } =
    useIAStore();
  const reviewDraft = useReviewDraft();
  const [criterion, setCriterion] = useState("");

  const isScience = SCIENCE_SUBJECTS.includes(subject);
  const criteria: IACriterion[] = isScience
    ? SCIENCE_IA_CRITERIA
    : DEFAULT_IA_CRITERIA;

  const handleSubmitForReview = useCallback(() => {
    if (!draftText.trim()) return;
    reviewDraft.mutate(
      {
        text: draftText,
        doc_type: docType,
        subject,
        criterion: criterion || undefined,
        previous_feedback: previousFeedback.length > 0 ? previousFeedback : undefined,
        version: previousFeedback.length + 1,
        session_id: sessionId,
      },
      {
        onSuccess: (data) => {
          addFeedback(data.response);
          useIAStore.getState().setActiveTab("review");
        },
      }
    );
  }, [
    draftText,
    docType,
    subject,
    criterion,
    previousFeedback,
    sessionId,
    reviewDraft,
    addFeedback,
  ]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <IAWordCounter text={draftText} />
        <div className="flex items-center gap-2">
          <Select value={criterion} onValueChange={setCriterion}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="All criteria" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All criteria</SelectItem>
              {criteria.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.id}: {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={handleSubmitForReview}
            disabled={!draftText.trim() || reviewDraft.isPending}
          >
            <Send className="mr-2 h-4 w-4" />
            {reviewDraft.isPending ? "Reviewing..." : "Submit for Review"}
          </Button>
        </div>
      </div>

      <Textarea
        value={draftText}
        onChange={(e) => setDraftText(e.target.value)}
        placeholder="Paste or write your IA draft here..."
        className="min-h-[400px] resize-y font-mono text-sm"
      />
    </div>
  );
}
