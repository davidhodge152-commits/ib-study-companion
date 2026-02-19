export interface ExamQuestion {
  number: number;
  question_text: string;
  marks: number;
  command_term?: string;
  topic?: string;
  model_answer?: string;
  paper?: number;
}

export interface ExamPaper {
  questions: ExamQuestion[];
  duration_minutes: number;
  reading_time_minutes: number;
  total_marks: number;
  subject: string;
  level: string;
  paper_number: number;
}

export interface ExamAnswer {
  question_number: number;
  answer: string;
}

export interface ExamSession {
  id: number;
  subject: string;
  level: string;
  paper_number: number;
  duration_minutes: number;
  questions: ExamQuestion[];
  answers?: ExamAnswer[];
  earned_marks?: number;
  total_marks: number;
  grade?: number;
  status: "in_progress" | "completed";
  created_at: string;
  completed_at?: string;
}

export interface ExamGenerateResponse {
  success: boolean;
  session_id: number;
  paper: ExamPaper;
}

export interface ExamSubmitResponse {
  success: boolean;
  grade: number;
}

export interface ExamResultsResponse {
  session: ExamSession;
}

export interface ExamHistoryResponse {
  sessions: ExamSession[];
}

export type ExamPhase =
  | "config"
  | "reading"
  | "active"
  | "review"
  | "submitting"
  | "results";
