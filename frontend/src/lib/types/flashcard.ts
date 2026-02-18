export interface FlashcardDeck {
  id: number | string;
  name: string;
  subject: string;
  card_count: number;
  due_count: number;
  mastery_pct: number;
  created_at: string;
}

export interface Flashcard {
  id: number | string;
  deck_id: number | string;
  front: string;
  back: string;
  difficulty: "easy" | "medium" | "hard";
  next_review: string;
  interval: number;
  ease_factor: number;
}

export interface ReviewResult {
  card_id: number | string;
  quality: 1 | 2 | 3 | 4 | 5;
}
