"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  BookOpen,
  Brain,
  Layers,
  BarChart3,
  MessageCircle,
  CalendarDays,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: BookOpen,
    title: "IB-Style Questions",
    description: "AI-generated practice questions tailored to your subjects and syllabus topics",
  },
  {
    icon: Brain,
    title: "AI Grading & Feedback",
    description: "Get instant, detailed feedback with examiner-style commentary on every answer",
  },
  {
    icon: Layers,
    title: "Smart Flashcards",
    description: "Spaced repetition flashcards that adapt to your learning pace",
  },
  {
    icon: MessageCircle,
    title: "AI Tutor",
    description: "Ask questions and get explanations on any IB topic with LaTeX math support",
  },
  {
    icon: BarChart3,
    title: "Insights & Analytics",
    description: "Track your progress, identify gaps, and get predicted grades",
  },
  {
    icon: CalendarDays,
    title: "Study Planner",
    description: "AI-generated study plans aligned with your exam schedule",
  },
];

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isLoading, isAuthenticated, router]);

  // Don't render landing page for authenticated users
  if (isLoading || isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Navbar */}
      <header className="border-b bg-card/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-8">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <BookOpen className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold">IB Study</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" asChild>
              <Link href="/login">Sign In</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Get Started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 py-16 text-center sm:px-8 sm:py-24">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
          Ace Your{" "}
          <span className="bg-gradient-to-r from-primary to-purple-500 bg-clip-text text-transparent">
            IB Exams
          </span>
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground sm:text-xl">
          AI-powered study companion that generates IB-style questions, grades
          your answers, and gives you personalised feedback — just like a real
          examiner.
        </p>
        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Button size="lg" asChild>
            <Link href="/register">
              Start Studying Free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/try">Try Without Account</Link>
          </Button>
        </div>
      </section>

      {/* Features */}
      <section className="border-t bg-muted/30 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-8">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">
            Everything you need for IB success
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-center text-muted-foreground">
            Built specifically for IB Diploma students, covering all subjects
            and assessment formats.
          </p>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="rounded-xl border bg-card p-6 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="mt-3 font-semibold">{title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="mx-auto max-w-2xl px-4 text-center sm:px-8">
          <h2 className="text-2xl font-bold sm:text-3xl">
            Ready to boost your grades?
          </h2>
          <p className="mt-2 text-muted-foreground">
            Join thousands of IB students using AI to study smarter, not harder.
          </p>
          <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Button size="lg" asChild>
              <Link href="/register">
                Create Free Account
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="ghost" asChild>
              <Link href="/login">Already have an account?</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="mx-auto max-w-6xl px-4 text-center text-sm text-muted-foreground sm:px-8">
          <p>IB Study Companion — AI-powered exam preparation for IB Diploma students</p>
        </div>
      </footer>
    </div>
  );
}
