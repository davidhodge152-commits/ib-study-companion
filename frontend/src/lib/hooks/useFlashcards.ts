"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../api-client";
import type { FlashcardDeck, Flashcard, ReviewResult } from "../types";

export function useFlashcardDecks() {
  return useQuery({
    queryKey: ["flashcards", "decks"],
    queryFn: () => api.get<{ decks: FlashcardDeck[] }>("/api/flashcards/decks"),
    staleTime: 2 * 60 * 1000,
  });
}

export function useFlashcardDeck(deckId: number) {
  return useQuery({
    queryKey: ["flashcards", "deck", deckId],
    queryFn: () => api.get<{ deck: FlashcardDeck; cards: Flashcard[] }>(`/api/flashcards/decks/${deckId}`),
    enabled: !!deckId,
  });
}

export function useDueCards(deckId?: number) {
  return useQuery({
    queryKey: ["flashcards", "due", deckId],
    queryFn: () =>
      api.get<{ cards: Flashcard[] }>(
        deckId ? `/api/flashcards/due?deck_id=${deckId}` : "/api/flashcards/due"
      ),
    staleTime: 60 * 1000,
  });
}

export function useReviewFlashcard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (review: ReviewResult) =>
      api.post("/api/flashcards/review", review),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["flashcards"] });
    },
    onError: () => {
      toast.error("Failed to save review. Please try again.");
    },
  });
}

interface CreateFlashcardInput {
  front: string;
  back: string;
  subject: string;
  topic?: string;
}

export function useCreateFlashcard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateFlashcardInput) =>
      api.post<{ success: true; card_id: string }>("/api/flashcards/create", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["flashcards"] });
      toast.success("Flashcard created successfully!");
    },
    onError: () => {
      toast.error("Failed to create flashcard. Please try again.");
    },
  });
}
