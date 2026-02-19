export interface DailyBriefing {
  response: string;
  burnout_risk?: string;
  burnout_signals?: string[];
  priority_subjects?: string[];
}

export interface SmartPlan {
  response: string;
  days_ahead?: number;
  deadlines?: string[];
}

export interface BurnoutCheck {
  risk_level: string;
  signals: string[];
  recommendation?: string;
}

export interface StudyDeadline {
  id: number;
  title: string;
  subject: string;
  deadline_type: string;
  due_date: string;
  importance: "low" | "medium" | "high";
  completed: boolean;
  created_at: string;
}

export interface ReprioritizeResponse {
  response: string;
  event?: string;
}
