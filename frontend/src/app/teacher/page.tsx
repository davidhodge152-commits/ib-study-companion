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

const mockClasses = [
  {
    id: "hl-math-2026",
    name: "HL Mathematics AA",
    studentCount: 18,
    avgGrade: 5.2,
  },
  {
    id: "sl-english-2026",
    name: "SL English A",
    studentCount: 24,
    avgGrade: 4.8,
  },
  {
    id: "hl-biology-2026",
    name: "HL Biology",
    studentCount: 15,
    avgGrade: 5.6,
  },
];

export default function TeacherDashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Teacher Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor student progress and manage your IB classes
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Total Students</CardDescription>
            <CardTitle className="text-3xl">
              {mockClasses.reduce((sum, c) => sum + c.studentCount, 0)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Active Classes</CardDescription>
            <CardTitle className="text-3xl">{mockClasses.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Average Grade</CardDescription>
            <CardTitle className="text-3xl">
              {mockClasses.length > 0
                ? (
                    mockClasses.reduce((sum, c) => sum + c.avgGrade, 0) /
                    mockClasses.length
                  ).toFixed(1)
                : "N/A"}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div>
        <h2 className="mb-4 text-lg font-semibold">Your Classes</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {mockClasses.map((cls) => (
            <Card key={cls.id} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <CardTitle className="text-lg">{cls.name}</CardTitle>
                <CardDescription>
                  {cls.studentCount} students
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Class Average
                  </span>
                  <span className="text-xl font-bold">{cls.avgGrade}</span>
                </div>
              </CardContent>
              <CardFooter>
                <Button asChild variant="outline" className="w-full">
                  <Link href={`/teacher/${cls.id}`}>View Class</Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
