"use client";

import { useState, useEffect, useMemo } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api-client";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

/* ------------------------------------------------------------------ */
/*  Static data                                                        */
/* ------------------------------------------------------------------ */

interface University {
  name: string;
  country: string;
  ibScore: string;
  notes: string;
}

const UNIVERSITIES: University[] = [
  { name: "University of Oxford", country: "UK", ibScore: "38-40", notes: "Subject-specific requirements vary by course" },
  { name: "University of Cambridge", country: "UK", ibScore: "40-42", notes: "Interviews required for most courses" },
  { name: "Imperial College London", country: "UK", ibScore: "38-40", notes: "Strong emphasis on maths and sciences" },
  { name: "University College London (UCL)", country: "UK", ibScore: "34-40", notes: "Wide range of programmes accepting IB" },
  { name: "London School of Economics (LSE)", country: "UK", ibScore: "37-38", notes: "Requires specific HL subjects" },
  { name: "University of Edinburgh", country: "UK", ibScore: "34-38", notes: "Popular with international IB students" },
  { name: "King's College London", country: "UK", ibScore: "35-38", notes: "Central London location" },
  { name: "University of St Andrews", country: "UK", ibScore: "36-38", notes: "Small collegiate feel, strong in sciences and arts" },
  { name: "University of Warwick", country: "UK", ibScore: "36-38", notes: "Top for business and economics" },
  { name: "University of Manchester", country: "UK", ibScore: "33-37", notes: "Large campus with wide course selection" },
  { name: "University of Toronto", country: "Canada", ibScore: "28-36", notes: "Grants advanced standing for HL 5+" },
  { name: "McGill University", country: "Canada", ibScore: "32-36", notes: "Strong IB recognition with credit transfer" },
  { name: "University of British Columbia", country: "Canada", ibScore: "30-34", notes: "Generous credit for HL subjects" },
  { name: "Harvard University", country: "USA", ibScore: "38+", notes: "Holistic admissions; IB valued but not required" },
  { name: "MIT", country: "USA", ibScore: "38+", notes: "HL credits can earn advanced standing" },
  { name: "Stanford University", country: "USA", ibScore: "38+", notes: "No specific IB requirements; holistic review" },
  { name: "Yale University", country: "USA", ibScore: "38+", notes: "IB diploma holders may receive credit for HL 7s" },
  { name: "Princeton University", country: "USA", ibScore: "38+", notes: "IB diploma recognised; credit for HL exams" },
  { name: "Columbia University", country: "USA", ibScore: "38+", notes: "Located in New York; values IB curriculum" },
  { name: "University of Pennsylvania", country: "USA", ibScore: "38+", notes: "Wharton business school popular with IB students" },
  { name: "ETH Zurich", country: "Switzerland", ibScore: "36+", notes: "Top technical university; requires specific HL maths/sciences" },
  { name: "University of Amsterdam", country: "Netherlands", ibScore: "34-36", notes: "Broad English-taught programmes" },
  { name: "Leiden University", country: "Netherlands", ibScore: "33-36", notes: "Oldest university in Netherlands, strong research" },
  { name: "University of Melbourne", country: "Australia", ibScore: "31-37", notes: "IB diploma widely recognised" },
  { name: "University of Sydney", country: "Australia", ibScore: "30-36", notes: "Generous credit for IB subjects" },
  { name: "National University of Singapore", country: "Singapore", ibScore: "38+", notes: "Top in Asia; competitive admissions" },
  { name: "University of Hong Kong", country: "Hong Kong", ibScore: "36+", notes: "IB diploma preferred; credit for HL 5+" },
  { name: "Trinity College Dublin", country: "Ireland", ibScore: "34-38", notes: "Historic campus; IB diploma accepted" },
];

interface Deadline {
  name: string;
  date: string;
  platform: string;
  description: string;
}

const DEADLINES: Deadline[] = [
  { name: "UCAS Oxford/Cambridge", date: "2026-10-15", platform: "UCAS", description: "Deadline for Oxford, Cambridge, medicine, dentistry, and veterinary courses" },
  { name: "UCAS Equal Consideration", date: "2027-01-15", platform: "UCAS", description: "Main UCAS deadline for equal consideration at all UK universities" },
  { name: "Common App Early Decision", date: "2026-11-01", platform: "Common App", description: "Early Decision/Early Action deadline for most US universities" },
  { name: "Common App Regular Decision", date: "2027-01-01", platform: "Common App", description: "Regular decision deadline for most US universities" },
  { name: "UC Application", date: "2026-11-30", platform: "UC System", description: "University of California system application deadline" },
  { name: "OUAC (Ontario)", date: "2027-01-15", platform: "OUAC", description: "Ontario Universities Application Centre deadline" },
  { name: "IB Extended Essay", date: "2027-03-15", platform: "IB", description: "Final submission deadline for Extended Essay (check with your school)" },
  { name: "IB Exams Begin", date: "2027-05-01", platform: "IB", description: "May examination session begins" },
  { name: "UCAS Extra Opens", date: "2027-02-25", platform: "UCAS", description: "UCAS Extra opens for students without offers" },
  { name: "IB Results Day", date: "2027-07-06", platform: "IB", description: "IB Diploma results released worldwide" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getCountdown(dateStr: string): string {
  const target = new Date(dateStr + "T23:59:59");
  const now = new Date();
  const diff = target.getTime() - now.getTime();

  if (diff <= 0) return "Passed";

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days > 60) {
    const months = Math.floor(days / 30);
    return `${months} month${months === 1 ? "" : "s"} away`;
  }
  if (days > 0) return `${days} day${days === 1 ? "" : "s"} away`;

  const hours = Math.floor(diff / (1000 * 60 * 60));
  return `${hours} hour${hours === 1 ? "" : "s"} away`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function AdmissionsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [personalStatement, setPersonalStatement] = useState("");
  const [, setTick] = useState(0);

  // Re-render every minute to keep countdown timers fresh
  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 60_000);
    return () => clearInterval(interval);
  }, []);

  const filteredUniversities = useMemo(() => {
    if (!searchQuery.trim()) return UNIVERSITIES;
    const q = searchQuery.toLowerCase();
    return UNIVERSITIES.filter(
      (u) =>
        u.name.toLowerCase().includes(q) ||
        u.country.toLowerCase().includes(q) ||
        u.notes.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  const psFeedback = useMutation({
    mutationFn: (statement: string) =>
      api.post<{ statement: string; metadata: Record<string, unknown> }>("/api/admissions/personal-statement", {
        target: "feedback", statement,
      }),
  });

  function handlePSSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!personalStatement.trim()) return;
    psFeedback.mutate(personalStatement.trim());
  }

  // Sort deadlines: upcoming first, passed last
  const sortedDeadlines = useMemo(() => {
    const now = new Date();
    return [...DEADLINES].sort((a, b) => {
      const aDate = new Date(a.date);
      const bDate = new Date(b.date);
      const aPassed = aDate < now;
      const bPassed = bDate < now;
      if (aPassed !== bPassed) return aPassed ? 1 : -1;
      return aDate.getTime() - bDate.getTime();
    });
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Admissions</h1>
        <p className="text-muted-foreground">
          University admissions guidance tailored to IB students
        </p>
      </div>

      {/* ---- University Search ---- */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">University Search</h2>
          <p className="text-sm text-muted-foreground">
            Explore popular universities that accept IB students
          </p>
        </div>

        <Input
          placeholder="Search by university name, country, or keyword..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-lg"
        />

        {filteredUniversities.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No universities match your search. Try a different keyword.
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredUniversities.map((uni) => (
              <Card key={uni.name} className="transition-shadow hover:shadow-md">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{uni.name}</CardTitle>
                  <CardDescription>{uni.country}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-1">
                  <p className="text-sm">
                    <span className="font-medium">Typical IB Score:</span>{" "}
                    {uni.ibScore}
                  </p>
                  <p className="text-xs text-muted-foreground">{uni.notes}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* ---- Personal Statement Feedback ---- */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Personal Statement Feedback</h2>
          <p className="text-sm text-muted-foreground">
            Paste your draft personal statement for AI-powered feedback on
            structure, content, and presentation.
          </p>
        </div>

        <Card>
          <form onSubmit={handlePSSubmit}>
            <CardContent className="space-y-4 pt-6">
              <div className="space-y-2">
                <Label htmlFor="ps-textarea">Your Personal Statement</Label>
                <Textarea
                  id="ps-textarea"
                  placeholder="Paste your personal statement here..."
                  rows={10}
                  value={personalStatement}
                  onChange={(e) => setPersonalStatement(e.target.value)}
                  className="min-h-[200px]"
                />
                <p className="text-xs text-muted-foreground">
                  {personalStatement.length > 0
                    ? `${personalStatement.split(/\s+/).filter(Boolean).length} words`
                    : "UCAS recommends up to 4,000 characters / ~47 lines"}
                </p>
              </div>
            </CardContent>
            <CardFooter className="flex flex-col items-start gap-3">
              <Button
                type="submit"
                disabled={
                  psFeedback.isPending || personalStatement.trim().length === 0
                }
              >
                {psFeedback.isPending
                  ? "Analysing..."
                  : "Get AI Feedback"}
              </Button>

              {psFeedback.isError && (
                <div className="w-full rounded-lg border border-destructive/20 bg-destructive/5 p-4">
                  <p className="text-sm text-destructive">
                    {psFeedback.error instanceof Error &&
                    psFeedback.error.message.includes("Upgrade")
                      ? "Personal statement feedback requires a Pro plan. Upgrade from the pricing page to unlock this feature."
                      : "Failed to get feedback. Please try again later."}
                  </p>
                  {psFeedback.error instanceof Error &&
                    psFeedback.error.message.includes("Upgrade") && (
                      <Button asChild variant="outline" size="sm" className="mt-2">
                        <Link href="/pricing">View Plans</Link>
                      </Button>
                    )}
                </div>
              )}

              {psFeedback.isSuccess && psFeedback.data?.statement && (
                <div className="w-full rounded-lg border bg-muted/50 p-4">
                  <h3 className="mb-2 text-sm font-semibold">AI Feedback</h3>
                  <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                    {psFeedback.data.statement}
                  </p>
                </div>
              )}
            </CardFooter>
          </form>
        </Card>
      </section>

      {/* ---- Deadlines ---- */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Key Deadlines</h2>
          <p className="text-sm text-muted-foreground">
            Important dates for IB students applying to university
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sortedDeadlines.map((deadline) => {
            const countdown = getCountdown(deadline.date);
            const isPassed = countdown === "Passed";

            return (
              <Card
                key={deadline.name}
                className={
                  isPassed
                    ? "opacity-60"
                    : "transition-shadow hover:shadow-md"
                }
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardDescription>{deadline.platform}</CardDescription>
                    <span
                      className={`text-xs font-medium ${
                        isPassed
                          ? "text-muted-foreground"
                          : "text-primary"
                      }`}
                    >
                      {countdown}
                    </span>
                  </div>
                  <CardTitle className="text-base">{deadline.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm font-medium">
                    {formatDate(deadline.date)}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {deadline.description}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>
    </div>
  );
}
