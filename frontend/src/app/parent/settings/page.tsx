"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface PrivacySettings {
  show_subject_grades: boolean;
  show_recent_activity: boolean;
  show_study_consistency: boolean;
  show_insights: boolean;
  show_exam_countdown: boolean;
}

const PRIVACY_OPTIONS: {
  key: keyof PrivacySettings;
  label: string;
  description: string;
}[] = [
  {
    key: "show_subject_grades",
    label: "Subject Grades",
    description:
      "Show your child's grades broken down by subject on the parent dashboard",
  },
  {
    key: "show_recent_activity",
    label: "Recent Activity",
    description:
      "Show recent study sessions, uploads, and other activity on the dashboard",
  },
  {
    key: "show_study_consistency",
    label: "Study Consistency",
    description:
      "Show study streak and consistency metrics so parents can see daily habits",
  },
  {
    key: "show_insights",
    label: "Performance Insights",
    description:
      "Show AI-generated insights about strengths, weaknesses, and study recommendations",
  },
  {
    key: "show_exam_countdown",
    label: "Exam Countdown",
    description:
      "Show the countdown timer to upcoming IB examination sessions",
  },
];

const DEFAULT_SETTINGS: PrivacySettings = {
  show_subject_grades: true,
  show_recent_activity: true,
  show_study_consistency: true,
  show_insights: true,
  show_exam_countdown: true,
};

export default function ParentSettingsPage() {
  const [settings, setSettings] = useState<PrivacySettings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  const saveMutation = useMutation({
    mutationFn: (data: PrivacySettings) =>
      api.post("/api/parent/privacy", data),
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const toggleSetting = useCallback((key: keyof PrivacySettings) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }));
    setSaved(false);
  }, []);

  const handleSave = () => {
    saveMutation.mutate(settings);
  };

  return (
    <div className="space-y-6">
      {/* Back link */}
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="sm">
          <Link href="/parent">Back to Dashboard</Link>
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-bold">Parent Settings</h1>
        <p className="text-muted-foreground">
          Configure privacy controls and monitoring preferences
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Privacy Controls</CardTitle>
          <CardDescription>
            Choose what information is visible on the parent dashboard. These
            settings help balance transparency with your child&apos;s privacy.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {PRIVACY_OPTIONS.map((option) => (
              <div
                key={option.key}
                className="flex items-start justify-between gap-4 rounded-lg border p-3"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium">{option.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {option.description}
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={settings[option.key]}
                  aria-label={`Toggle ${option.label}`}
                  onClick={() => toggleSetting(option.key)}
                  className={`relative inline-flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                    settings[option.key] ? "bg-primary" : "bg-muted"
                  }`}
                >
                  <span
                    className={`pointer-events-none block h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${
                      settings[option.key]
                        ? "translate-x-[18px]"
                        : "translate-x-0.5"
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </CardContent>
        <CardFooter className="flex items-center justify-between">
          <div>
            {saveMutation.error && (
              <p className="text-sm text-red-600 dark:text-red-400">
                Failed to save settings. Please try again.
              </p>
            )}
            {saved && (
              <p className="text-sm text-green-600 dark:text-green-400">
                Settings saved successfully.
              </p>
            )}
          </div>
          <Button
            onClick={handleSave}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? "Saving..." : "Save Settings"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
