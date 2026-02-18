import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

export default function AdmissionsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Admissions</h1>
        <p className="text-muted-foreground">
          University admissions guidance tailored to IB students
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>University Matcher</CardTitle>
            <CardDescription>
              Find universities that match your predicted grades and preferences
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Coming soon. We are building an AI-powered university matching
              engine that considers your IB subjects, predicted grades, location
              preferences, and programme interests.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Personal Statement</CardTitle>
            <CardDescription>
              Get AI feedback on your personal statement drafts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Coming soon. Upload your personal statement for structured
              feedback on content, structure, and presentation.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Deadlines Tracker</CardTitle>
            <CardDescription>
              Never miss an application deadline
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Coming soon. Track application deadlines for UCAS, Common App,
              and other platforms all in one place.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
