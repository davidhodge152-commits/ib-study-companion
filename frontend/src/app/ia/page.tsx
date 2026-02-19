import type { Metadata } from "next";
import { IAWorkspace } from "@/components/ia/IAWorkspace";

export const metadata: Metadata = {
  title: "IA Workspace",
};

export default function IAPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">IA Workspace</h1>
        <p className="text-muted-foreground">
          Write, review, and perfect your Internal Assessment with AI-powered
          criterion feedback
        </p>
      </div>
      <IAWorkspace />
    </div>
  );
}
