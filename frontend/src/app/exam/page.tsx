import type { Metadata } from "next";
import { ExamSession } from "@/components/exam/ExamSession";

export const metadata: Metadata = {
  title: "Exam Mode",
};

export default function ExamPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Exam Mode</h1>
        <p className="text-muted-foreground">
          Simulate real IB exam conditions with timed papers
        </p>
      </div>
      <ExamSession />
    </div>
  );
}
