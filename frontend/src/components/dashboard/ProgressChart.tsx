"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ProgressDataPoint } from "@/lib/types";

interface ProgressChartProps {
  data: ProgressDataPoint[];
  className?: string;
}

export function ProgressChart({ data, className }: ProgressChartProps) {
  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle>Score Trends</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            Complete some study sessions to see your progress over time.
          </p>
        ) : (
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={data}
                margin={{ top: 5, right: 10, left: -10, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  className="stroke-muted"
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  className="text-muted-foreground"
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 12 }}
                  className="text-muted-foreground"
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => `${value}%`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                    borderRadius: "0.5rem",
                    fontSize: "0.875rem",
                  }}
                  labelStyle={{ fontWeight: 600 }}
                  formatter={(value: number | undefined, name: string | undefined) => {
                    const v = value ?? 0;
                    if (name === "score") return [`${v}%`, "Score"];
                    if (name === "questions")
                      return [v, "Questions"];
                    return [v, name ?? ""];
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "hsl(var(--primary))" }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
