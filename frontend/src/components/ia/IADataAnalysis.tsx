"use client";

import { useState } from "react";
import { useAnalyzeData } from "@/lib/hooks/useIA";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { BarChart3 } from "lucide-react";

interface IADataAnalysisProps {
  subject: string;
  sessionId: number;
}

export function IADataAnalysis({ subject, sessionId }: IADataAnalysisProps) {
  const [rawData, setRawData] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const analyzeData = useAnalyzeData();

  const handleAnalyze = () => {
    if (!rawData.trim()) return;
    analyzeData.mutate({
      data: rawData,
      subject,
      hypothesis,
      session_id: sessionId,
    });
  };

  const result = analyzeData.data;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Paste your raw experimental data and hypothesis for AI-powered
        statistical analysis.
      </p>

      <div className="space-y-2">
        <Label>Hypothesis</Label>
        <Input
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          placeholder="e.g. Increasing temperature increases enzyme activity up to 40°C"
        />
      </div>

      <div className="space-y-2">
        <Label>Raw Data</Label>
        <Textarea
          value={rawData}
          onChange={(e) => setRawData(e.target.value)}
          placeholder="Paste your data here (CSV, table format, or plain text)..."
          className="min-h-[200px] font-mono text-sm"
        />
      </div>

      <Button
        onClick={handleAnalyze}
        disabled={!rawData.trim() || analyzeData.isPending}
      >
        <BarChart3 className="mr-2 h-4 w-4" />
        {analyzeData.isPending ? "Analyzing..." : "Analyze Data"}
      </Button>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Analysis Results</CardTitle>
          </CardHeader>
          <CardContent>
            <MarkdownRenderer content={result.response} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
