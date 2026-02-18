"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
import { useFlashcardDecks, useCreateFlashcard } from "@/lib/hooks/useFlashcards";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

function CreateCardDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");

  const createFlashcard = useCreateFlashcard();

  const canSubmit =
    front.trim().length > 0 &&
    back.trim().length > 0 &&
    subject.trim().length > 0;

  function resetForm() {
    setFront("");
    setBack("");
    setSubject("");
    setTopic("");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    createFlashcard.mutate(
      {
        front: front.trim(),
        back: back.trim(),
        subject: subject.trim(),
        topic: topic.trim() || undefined,
      },
      {
        onSuccess: () => {
          resetForm();
          onOpenChange(false);
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Flashcard</DialogTitle>
          <DialogDescription>
            Add a new flashcard with a question and answer.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="card-front">Front (Question)</Label>
            <Textarea
              id="card-front"
              placeholder="Enter the question or prompt..."
              value={front}
              onChange={(e) => setFront(e.target.value)}
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="card-back">Back (Answer)</Label>
            <Textarea
              id="card-back"
              placeholder="Enter the answer..."
              value={back}
              onChange={(e) => setBack(e.target.value)}
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="card-subject">Subject</Label>
            <Input
              id="card-subject"
              placeholder="e.g. Biology, Mathematics"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="card-topic">
              Topic <span className="text-muted-foreground">(optional)</span>
            </Label>
            <Input
              id="card-topic"
              placeholder="e.g. Cell Division, Calculus"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!canSubmit || createFlashcard.isPending}
            >
              {createFlashcard.isPending ? "Creating..." : "Create Card"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function FlashcardsPage() {
  const { data, isLoading, error } = useFlashcardDecks();
  const [dialogOpen, setDialogOpen] = useState(false);

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Flashcards</h1>
          <p className="text-muted-foreground">
            Review and master key concepts with spaced repetition
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Card
        </Button>
      </div>

      <CreateCardDialog open={dialogOpen} onOpenChange={setDialogOpen} />

      {decks.length === 0 ? (
        <EmptyState
          title="No flashcard decks yet"
          description="Upload study materials or create decks manually to start reviewing with spaced repetition."
          action={
            <div className="flex items-center gap-3">
              <Link
                href="/upload"
                className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Upload Materials
              </Link>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(true)}
              >
                <Plus className="mr-2 h-4 w-4" />
                Create Card
              </Button>
            </div>
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
