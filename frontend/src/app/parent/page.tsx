import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function ParentDashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Parent Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your child&apos;s IB progress and study habits
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/parent/settings">Settings</Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Study Streak</CardDescription>
            <CardTitle className="text-3xl">-- days</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Avg. Grade</CardDescription>
            <CardTitle className="text-3xl">--</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Questions This Week</CardDescription>
            <CardTitle className="text-3xl">--</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Subject Performance</CardTitle>
            <CardDescription>
              How your child is performing across their IB subjects
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Subject performance data will appear here once your child has
                completed enough study sessions.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Your child&apos;s latest study sessions and milestones
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Recent activity will appear here as your child uses the
                platform.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Weekly Summary</CardTitle>
          <CardDescription>
            An overview of study activity for the current week
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-32 items-center justify-center rounded-lg border border-dashed">
            <p className="text-sm text-muted-foreground">
              Weekly summary coming soon
            </p>
          </div>
        </CardContent>
        <CardFooter>
          <p className="text-xs text-muted-foreground">
            Email summaries can be configured in{" "}
            <Link href="/parent/settings" className="text-primary underline">
              settings
            </Link>
            .
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
