import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">
          Deep-dive into your study performance and habits
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Study Time</CardTitle>
            <CardDescription>
              Track how much time you spend studying each subject
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-40 items-center justify-center rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Study time chart coming soon
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Question Accuracy</CardTitle>
            <CardDescription>
              Your accuracy rate across different question types
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-40 items-center justify-center rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Accuracy chart coming soon
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Subject Comparison</CardTitle>
            <CardDescription>
              Compare your performance across all IB subjects
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-40 items-center justify-center rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Subject comparison coming soon
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Streak History</CardTitle>
            <CardDescription>
              Your daily study streak and consistency over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-40 items-center justify-center rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Streak history coming soon
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
