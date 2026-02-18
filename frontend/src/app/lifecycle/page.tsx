import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

const phases = [
  {
    title: "Year 1 - Foundation",
    description: "Build strong subject foundations and study habits",
    items: [
      "Subject selection guidance",
      "Core skills development",
      "Introduction to IA/EE topics",
      "CAS planning",
    ],
  },
  {
    title: "Year 1 - Mid-Year",
    description: "Deepen understanding and start internal assessments",
    items: [
      "IA research and drafting",
      "TOK essay exploration",
      "Mock exam preparation",
      "CAS activity tracking",
    ],
  },
  {
    title: "Year 2 - Intensive",
    description: "Finalize IAs and prepare for final examinations",
    items: [
      "IA final submissions",
      "Extended Essay completion",
      "TOK presentation prep",
      "Past paper practice",
    ],
  },
  {
    title: "Year 2 - Exam Season",
    description: "Final revision and exam execution",
    items: [
      "Subject-specific revision plans",
      "Exam technique refinement",
      "Stress management resources",
      "Results day preparation",
    ],
  },
];

export default function LifecyclePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">IB Lifecycle</h1>
        <p className="text-muted-foreground">
          Navigate every phase of your IB Diploma journey
        </p>
      </div>

      <div className="relative">
        {/* Timeline connector */}
        <div className="absolute left-6 top-0 hidden h-full w-0.5 bg-border md:block" />

        <div className="space-y-6">
          {phases.map((phase, i) => (
            <div key={i} className="relative md:pl-16">
              {/* Timeline dot */}
              <div className="absolute left-4 top-8 hidden h-5 w-5 rounded-full border-2 border-primary bg-background md:block" />

              <Card>
                <CardHeader>
                  <CardTitle>{phase.title}</CardTitle>
                  <CardDescription>{phase.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {phase.items.map((item) => (
                      <li
                        key={item}
                        className="flex items-center gap-2 text-sm text-muted-foreground"
                      >
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
