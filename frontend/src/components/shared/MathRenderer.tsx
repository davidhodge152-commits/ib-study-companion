"use client";

import katex from "katex";
import { useMemo } from "react";

interface MathRendererProps {
  math: string;
  display?: boolean;
  className?: string;
}

export function MathRenderer({
  math,
  display = false,
  className,
}: MathRendererProps) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(math, {
        displayMode: display,
        throwOnError: false,
        trust: true,
      });
    } catch {
      return math;
    }
  }, [math, display]);

  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
