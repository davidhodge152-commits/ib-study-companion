export interface FlashcardDeck {
  id: number;
  name: string;
  subject: string;
  card_count: number;
  due_count: number;
  mastery_pct: number;
  created_at: string;
}

export interface Flashcard {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  difficulty: "easy" | "medium" | "hard";
  next_review: string;
  interval: number;
  ease_factor: number;
}

export interface ReviewResult {
  card_id: number;
  quality: 1 | 2 | 3 | 4 | 5;
}
