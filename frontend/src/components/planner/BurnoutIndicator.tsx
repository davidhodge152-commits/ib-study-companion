"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface BurnoutIndicatorProps {
  riskLevel?: string;
  signals?: string[];
}

const riskConfig: Record<string, { label: string; className: string }> = {
  low: {
    label: "Low burnout",
    className: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20",
  },
  medium: {
    label: "Moderate burnout",
    className: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  },
  high: {
    label: "High burnout risk",
    className: "bg-destructive/10 text-destructive border-destructive/20",
  },
};

export function BurnoutIndicator({
  riskLevel,
  signals,
}: BurnoutIndicatorProps) {
  if (!riskLevel) return null;

  const config = riskConfig[riskLevel] ?? riskConfig.low;

  const badge = (
    <Badge variant="outline" className={cn("text-xs", config.className)}>
      {config.label}
    </Badge>
  );

  if (!signals || signals.length === 0) return badge;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <ul className="list-disc pl-4 text-xs">
            {signals.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
