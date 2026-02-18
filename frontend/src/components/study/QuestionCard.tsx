import type { StudyQuestion } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { cn } from "@/lib/utils";

interface QuestionCardProps {
  question: StudyQuestion;
  streamedContent?: string;
  className?: string;
}

export function QuestionCard({
  question,
  streamedContent,
  className,
}: QuestionCardProps) {
  const displayContent = streamedContent ?? question.question;

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge>{question.subject}</Badge>
          <Badge variant="secondary">{question.level}</Badge>
          {question.paper && (
            <Badge variant="outline">Paper {question.paper}</Badge>
          )}
          {question.command_term && (
            <Badge variant="outline">{question.command_term}</Badge>
          )}
        </div>
        <CardTitle className="mt-2 text-lg">
          {question.topic}
          <span className="ml-2 text-sm font-normal text-muted-foreground">
            [{question.marks} mark{question.marks !== 1 ? "s" : ""}]
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <MarkdownRenderer content={displayContent} />
      </CardContent>
    </Card>
  );
}
