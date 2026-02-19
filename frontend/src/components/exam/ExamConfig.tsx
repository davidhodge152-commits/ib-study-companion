"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSubjects } from "@/lib/hooks/useStudy";
import { Timer } from "lucide-react";

interface ExamConfigProps {
  onStart: (subject: string, level: string, paperNumber: number) => void;
  isGenerating: boolean;
}

const LEVELS = ["HL", "SL"];
const PAPERS = [1, 2, 3];

export function ExamConfig({ onStart, isGenerating }: ExamConfigProps) {
  const [subject, setSubject] = useState("");
  const [level, setLevel] = useState("HL");
  const [paperNumber, setPaperNumber] = useState(1);
  const { data: subjectsData } = useSubjects();

  const subjects = subjectsData?.subjects ?? [];

  return (
    <Card className="mx-auto max-w-lg">
      <CardHeader className="text-center">
        <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Timer className="h-6 w-6 text-primary" />
        </div>
        <CardTitle className="text-2xl">Timed Exam Mode</CardTitle>
        <CardDescription>
          Simulate real IB exam conditions with timed papers, reading time, and
          question navigation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Subject</label>
          <Select value={subject} onValueChange={setSubject}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Choose a subject" />
            </SelectTrigger>
            <SelectContent>
              {subjects.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Level</label>
            <Select value={level} onValueChange={setLevel}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LEVELS.map((l) => (
                  <SelectItem key={l} value={l}>
                    {l}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Paper</label>
            <Select
              value={String(paperNumber)}
              onValueChange={(v) => setPaperNumber(Number(v))}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAPERS.map((p) => (
                  <SelectItem key={p} value={String(p)}>
                    Paper {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Button
          className="w-full"
          size="lg"
          disabled={!subject || isGenerating}
          onClick={() => onStart(subject, level, paperNumber)}
        >
          {isGenerating ? "Generating Paper..." : "Start Exam"}
        </Button>
      </CardContent>
    </Card>
  );
}
