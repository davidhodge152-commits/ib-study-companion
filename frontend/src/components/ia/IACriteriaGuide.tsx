"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  SCIENCE_SUBJECTS,
  SCIENCE_IA_CRITERIA,
  DEFAULT_IA_CRITERIA,
} from "@/lib/types/ia";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface IACriteriaGuideProps {
  subject: string;
}

export function IACriteriaGuide({ subject }: IACriteriaGuideProps) {
  const [expanded, setExpanded] = useState(false);
  const isScience = SCIENCE_SUBJECTS.includes(subject);
  const criteria = isScience ? SCIENCE_IA_CRITERIA : DEFAULT_IA_CRITERIA;
  const totalMarks = criteria.reduce((sum, c) => sum + c.max_marks, 0);

  return (
    <div className="rounded-lg border">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div>
          <p className="text-sm font-medium">IB Criteria Reference</p>
          <p className="text-xs text-muted-foreground">
            {criteria.length} criteria, {totalMarks} marks total
          </p>
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-muted-foreground transition-transform",
            expanded && "rotate-180"
          )}
        />
      </button>
      {expanded && (
        <div className="border-t px-4 pb-4 pt-3 space-y-3">
          {criteria.map((c) => (
            <div key={c.id} className="space-y-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">
                  {c.id}
                </Badge>
                <span className="text-sm font-medium">{c.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {c.max_marks} marks
                </span>
              </div>
              <p className="pl-8 text-xs text-muted-foreground">
                {c.description}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
