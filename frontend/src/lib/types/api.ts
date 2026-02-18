export interface ApiError {
  error: string;
  message?: string;
  required_plan?: string;
  status?: number;
}

export interface DashboardData {
  stats: {
    total_questions: number;
    avg_grade: number;
    current_streak: number;
    upcoming_tasks: number;
  };
  recent_activity: ActivityItem[];
  progress: ProgressDataPoint[];
}

export interface ActivityItem {
  id: number;
  type: "study" | "flashcard" | "upload" | "community" | "tutor";
  description: string;
  timestamp: string;
  subject?: string;
}

export interface ProgressDataPoint {
  date: string;
  score: number;
  questions: number;
}

export interface InsightsData {
  total_answers: number;
  average_grade: number;
  average_percentage: number;
  grade_distribution: Record<string, number>;
  trend: number[];
  history: InsightsHistoryItem[];
  subject_stats: SubjectStat[];
  command_term_stats: CommandTermStat[];
  gaps: GapItem[];
  study_allocation: StudyAllocation[];
  insights: string[];
  syllabus_coverage: Record<string, SyllabusCoverage>;
  writing_profile: WritingProfile;
}

export interface InsightsHistoryItem {
  question: string;
  grade: number;
  percentage: number;
  mark: string;
  timestamp: string;
}

export interface SubjectStat {
  subject: string;
  count: number;
  avg_percentage: number;
}

export interface CommandTermStat {
  command_term: string;
  count: number;
  avg_percentage: number;
}

export interface GapItem {
  subject: string;
  status: string;
  gap: number;
  target_grade: number;
  current_avg: number;
}

export interface StudyAllocation {
  subject: string;
  percentage: number;
}

export interface SyllabusCoverage {
  overall: number;
  topics: {
    id: string;
    name: string;
    practiced: number;
    total: number;
    pct: number;
    hl_only: boolean;
  }[];
}

export interface WritingProfile {
  summary: string;
  verbosity: string;
  terminology_usage: string;
  argument_structure: string;
  common_patterns: string[];
  analyzed_count: number;
}

export interface PredictedGrade {
  subject: string;
  predicted: number;
  target: number;
  confidence: number;
}

export interface PlannerTask {
  id: number;
  title: string;
  description: string;
  due_date: string;
  completed: boolean;
  subject?: string;
  priority: "low" | "medium" | "high";
}

export interface TutorMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  images?: string[];
}

export interface TutorConversation {
  id: string;
  subject: string;
  topic: string;
  messages: TutorMessage[];
  created_at: string;
}

export interface CommunityPost {
  id: number;
  title: string;
  content: string;
  author: string;
  subject: string;
  votes: number;
  comment_count: number;
  created_at: string;
  user_vote?: -1 | 0 | 1;
}

export interface Comment {
  id: number;
  content: string;
  author_name: string;
  user_id: number;
  created_at: string;
}

export interface StudyGroup {
  id: number;
  name: string;
  description: string;
  member_count: number;
  subject: string;
  is_member: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  has_more: boolean;
}
