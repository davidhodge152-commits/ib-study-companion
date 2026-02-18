"use client";

import Link from "next/link";
import { useFlashcardDecks } from "@/lib/hooks/useFlashcards";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

export default function FlashcardsPage() {
  const { data, isLoading, error } = useFlashcardDecks();

  if (isLoading) return <LoadingSkeleton variant="card" count={6} />;

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
        <p className="text-destructive">
          Failed to load flashcard decks. Please try refreshing.
        </p>
      </div>
    );
  }

  const decks = data?.decks ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Flashcards</h1>
        <p className="text-muted-foreground">
          Review and master key concepts with spaced repetition
        </p>
      </div>

      {decks.length === 0 ? (
        <EmptyState
          title="No flashcard decks yet"
          description="Upload study materials or create decks manually to start reviewing with spaced repetition."
          action={
            <Link
              href="/upload"
              className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Upload Materials
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {decks.map((deck) => (
            <Card key={deck.id} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <CardTitle className="text-lg">{deck.name}</CardTitle>
                <CardDescription>{deck.subject}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold">{deck.card_count}</p>
                    <p className="text-xs text-muted-foreground">Cards</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-primary">
                      {deck.due_count}
                    </p>
                    <p className="text-xs text-muted-foreground">Due</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">
                      {Math.round(deck.mastery_pct)}%
                    </p>
                    <p className="text-xs text-muted-foreground">Mastery</p>
                  </div>
                </div>

                {/* Mastery progress bar */}
                <div className="mt-4 h-2 w-full rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary transition-all"
                    style={{ width: `${deck.mastery_pct}%` }}
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Link
                  href={`/flashcards/${deck.id}`}
                  className="inline-flex h-9 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                >
                  {deck.due_count > 0 ? `Review ${deck.due_count} Due` : "Browse Cards"}
                </Link>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
