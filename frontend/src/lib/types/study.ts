export interface StudyQuestion {
  id: string;
  subject: string;
  topic: string;
  level: "HL" | "SL";
  question: string;
  marks: number;
  command_term?: string;
  paper?: number;
}

export interface GradeResult {
  score: number;
  max_score: number;
  percentage: number;
  feedback: string;
  strengths: string[];
  improvements: string[];
  model_answer?: string;
  follow_up_questions?: string[];
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
