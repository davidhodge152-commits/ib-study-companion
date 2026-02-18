import type { GradeResult } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { cn } from "@/lib/utils";

interface GradeDisplayProps {
  result: GradeResult;
  className?: string;
}

function getPercentageColor(percentage: number): string {
  if (percentage >= 70) return "text-emerald-600 dark:text-emerald-400";
  if (percentage >= 50) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

function getPercentageBg(percentage: number): string {
  if (percentage >= 70) return "bg-emerald-50 dark:bg-emerald-500/10";
  if (percentage >= 50) return "bg-yellow-50 dark:bg-yellow-500/10";
  return "bg-red-50 dark:bg-red-500/10";
}

export function GradeDisplay({ result, className }: GradeDisplayProps) {
  const percentage = Math.round(result.percentage);

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle>Grade Result</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Score display */}
        <div
          className={cn(
            "flex items-center justify-center gap-4 rounded-lg p-6",
            getPercentageBg(percentage)
          )}
        >
          <div className="text-center">
            <div className="text-4xl font-bold">
              {result.score}
              <span className="text-2xl text-muted-foreground">
                /{result.max_score}
              </span>
            </div>
            <div
              className={cn("mt-1 text-lg font-semibold", getPercentageColor(percentage))}
            >
              {percentage}%
            </div>
          </div>
        </div>

        {/* Feedback */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Feedback</h4>
          <MarkdownRenderer content={result.feedback} />
        </div>

        {/* Strengths */}
        {result.strengths.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">Strengths</h4>
            <div className="flex flex-wrap gap-2">
              {result.strengths.map((strength, i) => (
                <Badge
                  key={i}
                  className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300"
                >
                  {strength}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Improvements */}
        {result.improvements.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">Areas for Improvement</h4>
            <div className="flex flex-wrap gap-2">
              {result.improvements.map((improvement, i) => (
                <Badge
                  key={i}
                  className="bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300"
                >
                  {improvement}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Model answer */}
        {result.model_answer && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">Model Answer</h4>
            <MarkdownRenderer content={result.model_answer} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
