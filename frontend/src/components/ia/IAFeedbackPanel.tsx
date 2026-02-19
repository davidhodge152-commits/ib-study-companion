"use client";

import { useIAStore } from "@/lib/stores/ia-store";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { EmptyState } from "@/components/shared/EmptyState";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useState } from "react";
import { MessageSquare } from "lucide-react";

export function IAFeedbackPanel() {
  const { previousFeedback } = useIAStore();
  const [selectedVersion, setSelectedVersion] = useState<string>("latest");

  if (previousFeedback.length === 0) {
    return (
      <EmptyState
        icon={<MessageSquare className="h-6 w-6" />}
        title="No feedback yet"
        description="Write your draft in the Editor tab and submit it for AI review."
      />
    );
  }

  const versionIndex =
    selectedVersion === "latest"
      ? previousFeedback.length - 1
      : Number(selectedVersion);
  const feedback = previousFeedback[versionIndex] ?? "";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Badge variant="secondary">
          {previousFeedback.length} review{previousFeedback.length !== 1 ? "s" : ""}
        </Badge>
        {previousFeedback.length > 1 && (
          <Select value={selectedVersion} onValueChange={setSelectedVersion}>
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="latest">Latest</SelectItem>
              {previousFeedback.map((_, i) => (
                <SelectItem key={i} value={String(i)}>
                  Version {i + 1}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            AI Feedback — Version{" "}
            {selectedVersion === "latest"
              ? previousFeedback.length
              : Number(selectedVersion) + 1}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <MarkdownRenderer content={feedback} />
        </CardContent>
      </Card>
    </div>
  );
}
