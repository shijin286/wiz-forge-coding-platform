export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type Category = "bug" | "security" | "performance" | "maintainability" | "style";

export interface User {
  id: number;
  email: string;
  name: string;
  created_at: string;
}

export interface Finding {
  id: number;
  source: "static" | "ai";
  rule_id: string;
  title: string;
  severity: Severity;
  category: Category;
  line: number | null;
  message: string;
  suggestion: string | null;
  confidence: "low" | "medium" | "high" | null;
}

export interface ReviewSummary {
  id: number;
  title: string;
  language: string;
  status: "processing" | "completed";
  ai_status: "skipped" | "pending" | "completed" | "failed";
  quality_score: number;
  grade: string;
  created_at: string;
  finding_counts: Partial<Record<Severity, number>>;
}

export interface ReviewDetail extends ReviewSummary {
  code: string;
  ai_summary: string | null;
  ai_strengths: string[] | null;
  ai_error: string | null;
  metrics: {
    total_lines: number;
    lines_of_code: number;
    comment_lines: number;
    blank_lines: number;
    comment_ratio: number;
    functions: number;
    avg_complexity: number;
    max_complexity: number | null;
  };
  completed_at: string | null;
  findings: Finding[];
  fixed_code: string | null;
  fixed_source: "static" | "ai" | null;
  fixes_applied: { line: number | null; rule_id: string; description: string }[] | null;
  fixes_remaining: { line: number | null; rule_id: string; title: string }[] | null;
  fixed_score: number | null;
  fixed_grade: string | null;
}

export interface Stats {
  total_reviews: number;
  average_score: number | null;
  total_findings: number;
  by_severity: Record<Severity, number>;
  by_category: Record<Category, number>;
  by_language: Record<string, number>;
  score_trend: { id: number; title: string; score: number; created_at: string }[];
  recent: ReviewSummary[];
}
