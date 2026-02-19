export interface CourseworkSession {
  id: number;
  doc_type: string;
  subject: string;
  title: string;
  current_phase: "proposal" | "research" | "drafting" | "revision" | "final";
  created_at: string;
  updated_at?: string;
}

export interface CourseworkDraft {
  id: number;
  session_id: number;
  version: number;
  text: string;
  word_count: number;
  feedback?: string;
  created_at: string;
}

export interface DataAnalysis {
  id: number;
  session_id: number;
  raw_data: string;
  hypothesis: string;
  result: string;
  created_at: string;
}

export interface FeasibilityResult {
  response: string;
  feasibility_score?: number;
  verdict?: string;
}

export interface DraftReviewResult {
  response: string;
  word_count?: number;
  version?: number;
}

export interface DataAnalysisResult {
  response: string;
  has_computed_results?: boolean;
}

export interface CourseworkSessionDetail {
  session: CourseworkSession;
  drafts: CourseworkDraft[];
  analyses: DataAnalysis[];
}

export type IAPhase = "proposal" | "research" | "drafting" | "revision" | "final";

export interface IACriterion {
  id: string;
  name: string;
  max_marks: number;
  description: string;
}

export const SCIENCE_SUBJECTS = [
  "Biology",
  "Chemistry",
  "Physics",
  "Environmental Systems and Societies",
];

export const SCIENCE_IA_CRITERIA: IACriterion[] = [
  { id: "A", name: "Personal Engagement", max_marks: 2, description: "Evidence of personal significance and interest" },
  { id: "B", name: "Exploration", max_marks: 6, description: "Research question, background information, methodology" },
  { id: "C", name: "Analysis", max_marks: 6, description: "Data collection, processing, and interpretation" },
  { id: "D", name: "Evaluation", max_marks: 6, description: "Conclusion, evaluation of methodology, extensions" },
  { id: "E", name: "Communication", max_marks: 4, description: "Structure, clarity, terminology, referencing" },
];

export const DEFAULT_IA_CRITERIA: IACriterion[] = [
  { id: "A", name: "Focus & Method", max_marks: 6, description: "Topic, research question, methodology" },
  { id: "B", name: "Knowledge & Understanding", max_marks: 6, description: "Sources, context, terminology" },
  { id: "C", name: "Critical Thinking", max_marks: 6, description: "Analysis, discussion, evaluation" },
  { id: "D", name: "Presentation", max_marks: 6, description: "Structure, layout, referencing" },
];
