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
  grade_distribution: Record<string, number>;
  trends: TrendDataPoint[];
  gaps: GapItem[];
  predicted_grades: PredictedGrade[];
}

export interface TrendDataPoint {
  date: string;
  subject: string;
  avg_score: number;
}

export interface GapItem {
  subject: string;
  topic: string;
  score: number;
  recommendation: string;
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
