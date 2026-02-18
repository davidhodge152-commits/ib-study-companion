import type { Metadata } from "next";
import { StudySession } from "@/components/study/StudySession";

export const metadata: Metadata = {
  title: "Study",
};

export default function StudyPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Study</h1>
        <p className="text-muted-foreground">
          Generate IB-style questions and get AI-powered feedback
        </p>
      </div>
      <StudySession />
    </div>
  );
}
