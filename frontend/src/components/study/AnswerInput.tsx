"use client";

import { Loader2, Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface AnswerInputProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  isGrading: boolean;
  className?: string;
}

export function AnswerInput({
  value,
  onChange,
  onSubmit,
  isGrading,
  className,
}: AnswerInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (value.trim() && !isGrading) {
        onSubmit();
      }
    }
  };

  return (
    <div className={cn("space-y-3", className)}>
      <Textarea
        placeholder="Type your answer here..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isGrading}
        className="min-h-32 resize-y"
      />
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Press {typeof navigator !== "undefined" && /Mac/.test(navigator.userAgent) ? "Cmd" : "Ctrl"}+Enter to submit
        </p>
        <Button
          onClick={onSubmit}
          disabled={!value.trim() || isGrading}
        >
          {isGrading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Send className="mr-2 h-4 w-4" />
          )}
          {isGrading ? "Grading..." : "Submit Answer"}
        </Button>
      </div>
    </div>
  );
}
