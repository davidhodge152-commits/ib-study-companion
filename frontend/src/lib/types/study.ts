export interface StudyQuestion {
  id: string;
  subject: string;
  topic: string;
  level: "HL" | "SL";
  question_text: string;
  question: string;
  marks: number;
  command_term?: string;
  paper?: number;
  model_answer?: string;
}

export interface GradeResult {
  mark_earned: number;
  mark_total: number;
  grade: number;
  percentage: number;
  strengths: string[];
  improvements: string[];
  examiner_tip: string;
  full_commentary: string;
  model_answer?: string;
  target_grade?: number;
  target_pct?: number;
  grade_gap?: number;
  command_term_check?: Record<string, unknown>;
  xp_earned?: number;
  total_xp?: number;
  level?: number;
  streak?: number;
  new_badges?: { name: string }[];
  daily_goal_pct?: number;
  flashcard_created?: boolean;
  misconceptions_detected?: string[];
}

export interface GenerateResponse {
  questions: StudyQuestion[];
  exam_paper_info?: {
    papers: {
      name: string;
      description: string;
      duration_minutes: number;
      marks: number;
      weighting_pct: number;
    }[];
    total_duration: number;
    total_marks: number;
  };
}

export interface StudySession {
  id: string;
  subject: string;
  topic: string;
  questions_answered: number;
  avg_score: number;
  started_at: string;
  ended_at?: string;
}
