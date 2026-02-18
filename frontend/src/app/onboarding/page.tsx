"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Loader2, Plus, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

const EXAM_SESSIONS = [
  "May 2026",
  "November 2026",
  "May 2027",
  "November 2027",
];

const IB_SUBJECTS = [
  "English A: Language & Literature",
  "English A: Literature",
  "Spanish B",
  "French B",
  "Mathematics: AA",
  "Mathematics: AI",
  "Physics",
  "Chemistry",
  "Biology",
  "Economics",
  "Business Management",
  "History",
  "Geography",
  "Psychology",
  "Computer Science",
  "Visual Arts",
  "Music",
  "Theatre",
  "TOK",
  "Extended Essay",
];

interface SubjectEntry {
  name: string;
  level: "HL" | "SL";
  target: number;
}

export default function OnboardingPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [examSession, setExamSession] = useState("");
  const [subjects, setSubjects] = useState<SubjectEntry[]>([
    { name: "", level: "HL", target: 7 },
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const addSubject = () => {
    if (subjects.length < 6) {
      setSubjects([...subjects, { name: "", level: "SL", target: 6 }]);
    }
  };

  const removeSubject = (idx: number) => {
    setSubjects(subjects.filter((_, i) => i !== idx));
  };

  const updateSubject = (
    idx: number,
    field: keyof SubjectEntry,
    value: string | number
  ) => {
    const updated = [...subjects];
    updated[idx] = { ...updated[idx], [field]: value };
    setSubjects(updated);
  };

  const handleSubmit = async () => {
    setError("");
    setIsSubmitting(true);
    try {
      await api.post("/api/onboarding", {
        name,
        exam_session: examSession,
        subjects: subjects.filter((s) => s.name),
      });
      queryClient.invalidateQueries({ queryKey: ["auth"] });
      toast.success("Profile created!");
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save profile");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-slate-50 p-8 dark:from-slate-900 dark:to-slate-800">
      <Card className="w-full max-w-2xl">
        <CardContent className="p-10">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold">Welcome to IB Study Companion</h1>
            <p className="mt-2 text-muted-foreground">
              Set up your profile to get personalized, target-driven study tools.
            </p>
          </div>

          {/* Step indicator */}
          <div className="mb-8 flex items-center justify-center gap-2">
            {[1, 2, 3].map((s) => (
              <div key={s} className="flex items-center gap-2">
                {s > 1 && (
                  <div className="h-0.5 w-8 bg-slate-200 dark:bg-slate-700" />
                )}
                <button
                  onClick={() => setStep(s)}
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold transition-colors",
                    step >= s
                      ? "bg-brand-600 text-white"
                      : "bg-slate-200 text-slate-500 dark:bg-slate-700"
                  )}
                >
                  {s}
                </button>
                <span className="hidden text-xs text-muted-foreground sm:inline">
                  {s === 1 ? "About You" : s === 2 ? "Subjects" : "Targets"}
                </span>
              </div>
            ))}
          </div>

          {error && (
            <div className="mb-6 rounded-lg border border-danger-500/20 bg-danger-50 p-4 text-sm text-danger-700 dark:bg-danger-500/10 dark:text-danger-500">
              {error}
            </div>
          )}

          {/* Step 1: About You */}
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">About You</h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Your Name</Label>
                  <Input
                    id="name"
                    placeholder="e.g. David"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="session">Exam Session</Label>
                  <Select value={examSession} onValueChange={setExamSession}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select session..." />
                    </SelectTrigger>
                    <SelectContent>
                      {EXAM_SESSIONS.map((s) => (
                        <SelectItem key={s} value={s}>
                          {s}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end pt-4">
                <Button
                  onClick={() => setStep(2)}
                  disabled={!name || !examSession}
                >
                  Next
                </Button>
              </div>
            </div>
          )}

          {/* Step 2: Subjects */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">Your Subjects</h2>
                <p className="text-sm text-muted-foreground">
                  Select up to 6 subjects. Set each as HL or SL.
                </p>
              </div>
              <div className="space-y-3">
                {subjects.map((subject, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Select
                      value={subject.name}
                      onValueChange={(v) => updateSubject(idx, "name", v)}
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select subject..." />
                      </SelectTrigger>
                      <SelectContent>
                        {IB_SUBJECTS.map((s) => (
                          <SelectItem key={s} value={s}>
                            {s}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Select
                      value={subject.level}
                      onValueChange={(v) =>
                        updateSubject(idx, "level", v as "HL" | "SL")
                      }
                    >
                      <SelectTrigger className="w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="HL">HL</SelectItem>
                        <SelectItem value="SL">SL</SelectItem>
                      </SelectContent>
                    </Select>
                    {subjects.length > 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeSubject(idx)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              {subjects.length < 6 && (
                <button
                  onClick={addSubject}
                  className="text-sm font-medium text-primary hover:underline"
                >
                  <Plus className="mr-1 inline h-3 w-3" />
                  Add Subject
                </button>
              )}
              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button
                  onClick={() => setStep(3)}
                  disabled={!subjects.some((s) => s.name)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}

          {/* Step 3: Targets */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">Set Your Targets</h2>
                <p className="text-sm text-muted-foreground">
                  What grade are you aiming for in each subject?
                </p>
              </div>
              <div className="space-y-3">
                {subjects
                  .filter((s) => s.name)
                  .map((subject, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div>
                        <p className="font-medium">{subject.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {subject.level}
                        </p>
                      </div>
                      <Select
                        value={String(subject.target)}
                        onValueChange={(v) =>
                          updateSubject(idx, "target", parseInt(v))
                        }
                      >
                        <SelectTrigger className="w-20">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {[7, 6, 5, 4, 3].map((g) => (
                            <SelectItem key={g} value={String(g)}>
                              {g}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
              </div>
              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep(2)}>
                  Back
                </Button>
                <Button onClick={handleSubmit} disabled={isSubmitting}>
                  {isSubmitting ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : null}
                  Start Studying
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
