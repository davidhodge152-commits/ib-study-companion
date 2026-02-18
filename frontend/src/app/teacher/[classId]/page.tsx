import Link from "next/link";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ClassDetailPageProps {
  params: Promise<{ classId: string }>;
}

export default async function ClassDetailPage({ params }: ClassDetailPageProps) {
  const { classId } = await params;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="sm">
          <Link href="/teacher">Back to Dashboard</Link>
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-bold">Class: {classId}</h1>
        <p className="text-muted-foreground">
          Student performance overview and class management
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Students</CardDescription>
            <CardTitle className="text-3xl">--</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Avg. Score</CardDescription>
            <CardTitle className="text-3xl">--</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Assignments Due</CardDescription>
            <CardTitle className="text-3xl">--</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Student Roster</CardTitle>
          <CardDescription>
            View individual student progress and performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-40 items-center justify-center rounded-lg border border-dashed">
            <p className="text-sm text-muted-foreground">
              Student roster for class &quot;{classId}&quot; will appear here
              once data is loaded.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Class Performance</CardTitle>
          <CardDescription>
            Grade distribution and trends for this class
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-40 items-center justify-center rounded-lg border border-dashed">
            <p className="text-sm text-muted-foreground">
              Performance charts coming soon
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
