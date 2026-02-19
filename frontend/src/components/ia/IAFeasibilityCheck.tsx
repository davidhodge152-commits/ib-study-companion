"use client";

import { useState } from "react";
import { useCheckFeasibility } from "@/lib/hooks/useIA";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";

interface IAFeasibilityCheckProps {
  subject: string;
  docType: string;
}

export function IAFeasibilityCheck({
  subject,
  docType,
}: IAFeasibilityCheckProps) {
  const [topic, setTopic] = useState("");
  const checkFeasibility = useCheckFeasibility();

  const handleCheck = () => {
    if (!topic.trim()) return;
    checkFeasibility.mutate({ topic, subject, doc_type: docType });
  };

  const result = checkFeasibility.data;
  const score = result?.feasibility_score ?? null;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-muted-foreground">
          Describe your IA topic proposal and get AI feedback on feasibility.
        </p>
      </div>

      <Textarea
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Describe your topic proposal in detail..."
        className="min-h-[120px]"
      />

      <Button
        onClick={handleCheck}
        disabled={!topic.trim() || checkFeasibility.isPending}
      >
        <Search className="mr-2 h-4 w-4" />
        {checkFeasibility.isPending ? "Checking..." : "Check Feasibility"}
      </Button>

      {result && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Feasibility Result</CardTitle>
              <div className="flex items-center gap-2">
                {score !== null && (
                  <Badge
                    variant="secondary"
                    className={cn(
                      score >= 7
                        ? "bg-green-500/10 text-green-700 dark:text-green-400"
                        : score >= 4
                          ? "bg-amber-500/10 text-amber-700 dark:text-amber-400"
                          : "bg-destructive/10 text-destructive"
                    )}
                  >
                    Score: {score}/10
                  </Badge>
                )}
                {result.verdict && (
                  <Badge variant="outline">{result.verdict}</Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <MarkdownRenderer content={result.response} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
