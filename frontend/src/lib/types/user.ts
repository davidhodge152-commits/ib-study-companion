export interface User {
  id: number;
  email: string;
  name: string;
  exam_session?: string;
  plan?: "free" | "pro" | "premium";
  credits?: number;
  created_at?: string;
  locale?: string;
  role?: "student" | "teacher" | "parent";
  email_verified?: boolean;
}

export interface UserProfile {
  name: string;
  exam_session: string;
  subjects: Subject[];
  onboarding_complete: boolean;
}

export interface Subject {
  id: number;
  name: string;
  level: "HL" | "SL";
  topics: string[];
}

export interface Gamification {
  level: number;
  total_xp: number;
  xp_progress_pct: number;
  current_streak: number;
  streak_freeze_available: number;
  daily_xp_today: number;
  daily_goal_xp: number;
  daily_goal_pct: number;
}
