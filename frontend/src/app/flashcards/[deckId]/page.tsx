"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  useFlashcardDeck,
  useDueCards,
  useReviewFlashcard,
} from "@/lib/hooks/useFlashcards";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import type { Flashcard, ReviewResult } from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Mode = "browse" | "review";
type Quality = ReviewResult["quality"];

interface ReviewRecord {
  cardId: number | string;
  quality: Quality;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const QUALITY_OPTIONS: { quality: Quality; label: string; color: string; keys: string }[] = [
  { quality: 1, label: "Again", color: "bg-red-500 hover:bg-red-600 text-white", keys: "1" },
  { quality: 2, label: "Hard", color: "bg-orange-500 hover:bg-orange-600 text-white", keys: "2" },
  { quality: 3, label: "Good", color: "bg-blue-500 hover:bg-blue-600 text-white", keys: "3" },
  { quality: 4, label: "Easy", color: "bg-emerald-500 hover:bg-emerald-600 text-white", keys: "4" },
];

const DIFFICULTY_VARIANT: Record<Flashcard["difficulty"], "default" | "secondary" | "destructive"> = {
  easy: "default",
  medium: "secondary",
  hard: "destructive",
};

// ---------------------------------------------------------------------------
// FlippableCard component (shared between Browse & Review)
// ---------------------------------------------------------------------------

function FlippableCard({
  card,
  flipped,
  onFlip,
  size = "normal",
}: {
  card: Flashcard;
  flipped: boolean;
  onFlip: () => void;
  size?: "normal" | "large";
}) {
  const height = size === "large" ? "min-h-[320px]" : "min-h-[200px]";

  return (
    <div
      className={`perspective-[1000px] w-full cursor-pointer ${height}`}
      onClick={onFlip}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onFlip();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={flipped ? "Showing answer. Click to show question." : "Showing question. Click to reveal answer."}
    >
      <div
        className={`relative h-full w-full transition-transform duration-500 [transform-style:preserve-3d] ${
          flipped ? "[transform:rotateY(180deg)]" : ""
        }`}
      >
        {/* Front face */}
        <div className="absolute inset-0 flex flex-col items-center justify-center rounded-xl border bg-card p-6 shadow-sm [backface-visibility:hidden]">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Question
          </p>
          <div className="w-full text-center">
            <MarkdownRenderer content={card.front} className="text-lg" />
          </div>
        </div>

        {/* Back face */}
        <div className="absolute inset-0 flex flex-col items-center justify-center rounded-xl border bg-card p-6 shadow-sm [backface-visibility:hidden] [transform:rotateY(180deg)]">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Answer
          </p>
          <div className="w-full text-center">
            <MarkdownRenderer content={card.back} className="text-lg" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ReviewSession sub-component
// ---------------------------------------------------------------------------

function ReviewSession({
  dueCards,
  onComplete,
}: {
  dueCards: Flashcard[];
  onComplete: () => void;
}) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [finished, setFinished] = useState(false);

  const reviewMutation = useReviewFlashcard();
  const currentCard = dueCards[currentIndex];
  const total = dueCards.length;
  const progressPct = total > 0 ? Math.round((currentIndex / total) * 100) : 0;

  const handleRate = useCallback(
    (quality: Quality) => {
      if (!currentCard) return;

      // Submit review
      reviewMutation.mutate({ card_id: currentCard.id, quality });

      // Track locally
      setReviews((prev) => [...prev, { cardId: currentCard.id, quality }]);

      // Advance or finish
      if (currentIndex + 1 >= total) {
        setFinished(true);
      } else {
        setCurrentIndex((i) => i + 1);
        setFlipped(false);
      }
    },
    [currentCard, currentIndex, total, reviewMutation],
  );

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!flipped && (e.key === " " || e.key === "Enter")) {
        e.preventDefault();
        setFlipped(true);
        return;
      }
      if (flipped) {
        const num = parseInt(e.key);
        if (num >= 1 && num <= 4) {
          e.preventDefault();
          handleRate(QUALITY_OPTIONS[num - 1].quality);
        }
      }
    },
    [flipped, handleRate],
  );

  // Summary screen
  if (finished) {
    const avgQuality =
      reviews.length > 0
        ? reviews.reduce((sum, r) => sum + r.quality, 0) / reviews.length
        : 0;

    const qualityDistribution = reviews.reduce(
      (acc, r) => {
        acc[r.quality] = (acc[r.quality] || 0) + 1;
        return acc;
      },
      {} as Record<number, number>,
    );

    return (
      <div className="mx-auto max-w-lg space-y-6">
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Review Complete!</CardTitle>
            <CardDescription>
              Great job finishing your review session.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Stats row */}
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="rounded-lg bg-muted/50 p-4">
                <p className="text-3xl font-bold text-primary">{reviews.length}</p>
                <p className="text-sm text-muted-foreground">Cards Reviewed</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-4">
                <p className="text-3xl font-bold text-primary">
                  {avgQuality.toFixed(1)}
                </p>
                <p className="text-sm text-muted-foreground">Avg Quality</p>
              </div>
            </div>

            {/* Quality breakdown */}
            <div className="space-y-2">
              <p className="text-sm font-medium">Rating Breakdown</p>
              <div className="space-y-1.5">
                {QUALITY_OPTIONS.map(({ quality, label }) => {
                  const count = qualityDistribution[quality] || 0;
                  const pct = reviews.length > 0 ? (count / reviews.length) * 100 : 0;
                  return (
                    <div key={quality} className="flex items-center gap-3">
                      <span className="w-12 text-sm text-muted-foreground">{label}</span>
                      <div className="flex-1">
                        <div className="h-2 w-full rounded-full bg-muted">
                          <div
                            className="h-2 rounded-full bg-primary transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                      <span className="w-8 text-right text-sm font-medium">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex gap-3">
            <Button variant="outline" className="flex-1" asChild>
              <Link href="/flashcards">All Decks</Link>
            </Button>
            <Button className="flex-1" onClick={onComplete}>
              Done
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (!currentCard) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No cards to review.</p>
      </div>
    );
  }

  return (
    <div
      className="mx-auto max-w-2xl space-y-6"
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      {/* Progress header */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Card {currentIndex + 1} of {total}
          </span>
          <span className="font-medium text-primary">{progressPct}%</span>
        </div>
        <Progress value={progressPct} />
      </div>

      {/* Flashcard */}
      <FlippableCard
        card={currentCard}
        flipped={flipped}
        onFlip={() => setFlipped((f) => !f)}
        size="large"
      />

      {/* Action area */}
      {!flipped ? (
        <div className="text-center">
          <Button
            size="lg"
            onClick={() => setFlipped(true)}
            className="min-w-[200px]"
          >
            Show Answer
          </Button>
          <p className="mt-2 text-xs text-muted-foreground">
            Press Space or click the card to reveal
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-center text-sm font-medium text-muted-foreground">
            How well did you know this?
          </p>
          <div className="grid grid-cols-4 gap-2">
            {QUALITY_OPTIONS.map(({ quality, label, color, keys }) => (
              <Button
                key={quality}
                className={color}
                onClick={() => handleRate(quality)}
                disabled={reviewMutation.isPending}
              >
                <span className="flex flex-col items-center gap-0.5">
                  <span className="text-sm font-semibold">{label}</span>
                  <span className="text-[10px] opacity-75">({keys})</span>
                </span>
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Difficulty badge */}
      <div className="flex justify-center">
        <Badge variant={DIFFICULTY_VARIANT[currentCard.difficulty]}>
          {currentCard.difficulty}
        </Badge>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BrowseGrid sub-component
// ---------------------------------------------------------------------------

function BrowseGrid({ cards }: { cards: Flashcard[] }) {
  const [flippedCards, setFlippedCards] = useState<Set<number | string>>(new Set());

  const toggleCard = useCallback((id: number | string) => {
    setFlippedCards((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  if (cards.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">This deck has no cards yet.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card) => (
        <FlippableCard
          key={card.id}
          card={card}
          flipped={flippedCards.has(card.id)}
          onFlip={() => toggleCard(card.id)}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function DeckDetailPage() {
  const params = useParams<{ deckId: string }>();
  const deckId = Number(params.deckId);

  const [mode, setMode] = useState<Mode>("browse");

  const { data: deckData, isLoading: deckLoading, error: deckError } = useFlashcardDeck(deckId);
  const { data: dueData, isLoading: dueLoading } = useDueCards(deckId);

  const deck = deckData?.deck;
  const allCards = deckData?.cards ?? [];
  const dueCards = dueData?.cards ?? [];

  // Whenever the user finishes a review, switch back to browse
  const handleReviewComplete = useCallback(() => {
    setMode("browse");
  }, []);

  // Memoised stats for the header
  const stats = useMemo(
    () => ({
      total: deck?.card_count ?? allCards.length,
      due: dueCards.length,
      mastery: deck?.mastery_pct ?? 0,
    }),
    [deck, allCards.length, dueCards.length],
  );

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------

  if (deckLoading || dueLoading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton variant="page" />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Error state
  // ---------------------------------------------------------------------------

  if (deckError || !deck) {
    return (
      <div className="space-y-4">
        <Link
          href="/flashcards"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          &larr; Back to Decks
        </Link>
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
          <p className="text-destructive">
            {deckError ? "Failed to load this deck. Please try again." : "Deck not found."}
          </p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Navigation */}
      <Link
        href="/flashcards"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        &larr; Back to Decks
      </Link>

      {/* Deck header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">{deck.name}</h1>
          <p className="text-muted-foreground">{deck.subject}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={mode === "browse" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("browse")}
          >
            Browse
          </Button>
          <Button
            variant={mode === "review" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("review")}
            disabled={dueCards.length === 0}
          >
            Review{dueCards.length > 0 ? ` (${dueCards.length})` : ""}
          </Button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-4">
            <span className="text-2xl font-bold">{stats.total}</span>
            <span className="text-xs text-muted-foreground">Total Cards</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-4">
            <span className="text-2xl font-bold text-primary">{stats.due}</span>
            <span className="text-xs text-muted-foreground">Due for Review</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-4">
            <span className="text-2xl font-bold">{Math.round(stats.mastery)}%</span>
            <span className="text-xs text-muted-foreground">Mastery</span>
          </CardContent>
        </Card>
      </div>

      {/* Mastery progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Mastery Progress</span>
          <span>{Math.round(stats.mastery)}%</span>
        </div>
        <Progress value={stats.mastery} />
      </div>

      {/* Mode content */}
      {mode === "review" ? (
        dueCards.length > 0 ? (
          <ReviewSession dueCards={dueCards} onComplete={handleReviewComplete} />
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-lg font-medium">All caught up!</p>
              <p className="mt-1 text-sm text-muted-foreground">
                No cards are due for review right now. Check back later or browse your cards.
              </p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setMode("browse")}
              >
                Browse Cards
              </Button>
            </CardContent>
          </Card>
        )
      ) : (
        <BrowseGrid cards={allCards} />
      )}
    </div>
  );
}
