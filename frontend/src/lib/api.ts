import type { PullRequestResult, ReviewDetail, ReviewSummary, Stats, User } from "./types";

const TOKEN_KEY = "wizforge.token";

export const tokenStore = {
  get: () => {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set: (t: string) => {
    try { localStorage.setItem(TOKEN_KEY, t); } catch { /* storage unavailable */ }
  },
  clear: () => {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`/api${path}`, { ...init, headers });
  if (res.status === 401 && token) {
    tokenStore.clear();
    window.dispatchEvent(new Event("wizforge:logout"));
  }
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = typeof body.detail === "string"
        ? body.detail
        : Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join("; ") : message;
    } catch { /* not JSON */ }
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

interface TokenResponse { access_token: string; user: User }

export const api = {
  register: (email: string, name: string, password: string) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify({ email, name, password }) }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<User>("/auth/me"),

  languages: () => request<{ id: string; label: string }[]>("/languages"),
  detectLanguage: (code: string) =>
    request<{ language: string | null }>("/detect-language", { method: "POST", body: JSON.stringify({ code }) }),
  stats: () => request<Stats>("/stats"),
  createReview: (body: { title: string; language: string; code: string; use_ai: boolean }) =>
    request<ReviewDetail>("/reviews", { method: "POST", body: JSON.stringify(body) }),
  listReviews: (params: { search?: string; language?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && q.set(k, String(v)));
    return request<{ items: ReviewSummary[]; total: number }>(`/reviews?${q}`);
  },
  getReview: (id: number) => request<ReviewDetail>(`/reviews/${id}`),
  deleteReview: (id: number) => request<void>(`/reviews/${id}`, { method: "DELETE" }),
  downloadReport: async (id: number) => {
    const res = await fetch(`/api/reviews/${id}/report.pdf`, {
      headers: { Authorization: `Bearer ${tokenStore.get() ?? ""}` },
    });
    if (!res.ok) throw new ApiError(res.status, "Could not create the PDF report");
    const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "report.pdf";
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  },
  generateTests: (id: number, useAI: boolean) =>
    request<{ source: "static" | "ai"; framework: string; filename: string; code: string; notes: string; count: number | null }>(
      `/reviews/${id}/tests`, { method: "POST", body: JSON.stringify({ use_ai: useAI }) }),
  reviewPullRequest: (url: string, useAI: boolean) =>
    request<PullRequestResult>("/import/github-pr", { method: "POST", body: JSON.stringify({ url, use_ai: useAI }) }),
  importFromGithub: (url: string) =>
    request<{ filename: string; language: string; code: string }>("/import/github", {
      method: "POST", body: JSON.stringify({ url }),
    }),
  health: () => request<{ status: string; ai_enabled: boolean; ai_configured: boolean; ai_model: string }>("/health"),
};
