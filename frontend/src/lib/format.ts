import type { Severity } from "./types";

export const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];

export const SEVERITY_STYLE: Record<Severity, { text: string; bg: string; dot: string }> = {
  critical: { text: "text-sev-critical", bg: "bg-sev-critical/10 border-sev-critical/30", dot: "bg-sev-critical" },
  high: { text: "text-sev-high", bg: "bg-sev-high/10 border-sev-high/30", dot: "bg-sev-high" },
  medium: { text: "text-sev-medium", bg: "bg-sev-medium/10 border-sev-medium/30", dot: "bg-sev-medium" },
  low: { text: "text-sev-low", bg: "bg-sev-low/10 border-sev-low/30", dot: "bg-sev-low" },
  info: { text: "text-sev-info", bg: "bg-sev-info/10 border-sev-info/30", dot: "bg-sev-info" },
};

export const LANGUAGE_LABEL: Record<string, string> = {
  python: "Python", javascript: "JavaScript", typescript: "TypeScript", java: "Java",
  cpp: "C++", c: "C", go: "Go", other: "Other",
};

/** Monaco's language id for each of our language ids. */
export const MONACO_LANGUAGE: Record<string, string> = {
  python: "python", javascript: "javascript", typescript: "typescript", java: "java",
  cpp: "cpp", c: "c", go: "go", other: "plaintext",
};

const EXTENSIONS: Record<string, string> = {
  py: "python", js: "javascript", jsx: "javascript", mjs: "javascript", cjs: "javascript",
  ts: "typescript", tsx: "typescript", java: "java", cpp: "cpp", cc: "cpp", cxx: "cpp", hpp: "cpp",
  c: "c", h: "c", go: "go",
};

export function languageFromFilename(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return EXTENSIONS[ext] ?? "other";
}

export function scoreColor(score: number): string {
  if (score >= 90) return "#34d399";
  if (score >= 80) return "#a3e635";
  if (score >= 70) return "#facc15";
  if (score >= 55) return "#fb923c";
  return "#f43f5e";
}

export function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const units: [number, string][] = [[86400 * 30, "mo"], [86400, "d"], [3600, "h"], [60, "m"]];
  for (const [size, label] of units) if (seconds >= size) return `${Math.floor(seconds / size)}${label} ago`;
  return "just now";
}
