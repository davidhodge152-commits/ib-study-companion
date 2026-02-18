import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function ParentSettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="sm">
          <Link href="/parent">Back to Dashboard</Link>
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-bold">Parent Settings</h1>
        <p className="text-muted-foreground">
          Configure notifications and monitoring preferences
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
            <CardDescription>
              Choose which updates you receive about your child&apos;s progress
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                {
                  label: "Weekly Progress Report",
                  description:
                    "Receive a summary email every Sunday with study activity",
                },
                {
                  label: "Grade Alerts",
                  description:
                    "Get notified when your child scores below a threshold",
                },
                {
                  label: "Streak Reminders",
                  description:
                    "Notified when the study streak is about to break",
                },
                {
                  label: "Milestone Achievements",
                  description:
                    "Celebrate when your child reaches study milestones",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="flex items-start justify-between gap-4 rounded-lg border p-3"
                >
                  <div>
                    <p className="text-sm font-medium">{item.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.description}
                    </p>
                  </div>
                  <div className="flex h-6 w-10 shrink-0 items-center rounded-full bg-muted px-0.5">
                    <div className="h-5 w-5 rounded-full bg-muted-foreground/40 transition-transform" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Linked Students</CardTitle>
            <CardDescription>
              Manage which student accounts are linked to your parent dashboard
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-40 items-center justify-center rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Student linking will be available soon. Your child can send you
                an invite from their account settings.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
