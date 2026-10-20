import { AlertTriangle, ArrowLeft, Bot, CheckCircle2, Cpu, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CodeEditor from "../components/CodeEditor";
import CorrectedCode from "../components/CorrectedCode";
import FindingCard from "../components/FindingCard";
import { ErrorBox, ScoreRing, Spinner, Tag } from "../components/ui";
import { api } from "../lib/api";
import { LANGUAGE_LABEL, SEVERITIES, SEVERITY_STYLE } from "../lib/format";
import type { ReviewDetail as Review, Severity } from "../lib/types";

type SourceFilter = "all" | "static" | "ai";

export default function ReviewDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState("");
  const [focusLine, setFocusLine] = useState<number | null>(null);
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [source, setSource] = useState<SourceFilter>("all");

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const load = async () => {
      try {
        const r = await api.getReview(Number(id));
        if (cancelled) return;
        setReview(r);
        if (r.status === "processing") timer = window.setTimeout(load, 2500);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load review");
      }
    };
    load();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [id]);

  const findings = useMemo(() => {
    if (!review) return [];
    return review.findings
      .filter((f) => (severity === "all" || f.severity === severity) && (source === "all" || f.source === source))
      .sort((a, b) => SEVERITIES.indexOf(a.severity) - SEVERITIES.indexOf(b.severity) || (a.line ?? 0) - (b.line ?? 0));
  }, [review, severity, source]);

  if (error) return <ErrorBox message={error} />;
  if (!review) return <Spinner label="Loading review…" />;

  const remove = async () => {
    if (!confirm("Delete this review? This cannot be undone.")) return;
    await api.deleteReview(review.id);
    navigate("/history");
  };

  const m = review.metrics;
  const staticCount = review.findings.filter((f) => f.source === "static").length;
  const aiCount = review.findings.length - staticCount;

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <Link to="/history" className="mb-2 inline-flex items-center gap-1 text-xs text-ink-400 hover:text-ink-100"><ArrowLeft size={13} /> History</Link>
          <h1 className="truncate text-2xl font-semibold tracking-tight">{review.title}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-ink-400">
            <Tag>{LANGUAGE_LABEL[review.language]}</Tag>
            <span>{new Date(review.created_at).toLocaleString()}</span>
          </div>
        </div>
        <button onClick={remove} className="btn-ghost"><Trash2 size={15} /> Delete</button>
      </div>

      {/* overview */}
      <div className="mb-6 grid gap-4 lg:grid-cols-[auto_1fr]">
        <div className="card flex items-center gap-6 p-5">
          <ScoreRing score={review.quality_score} grade={review.grade} />
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <Metric label="Lines of code" value={m.lines_of_code} />
            <Metric label="Functions" value={m.functions} />
            <Metric label="Avg complexity" value={m.avg_complexity} />
            <Metric label="Max complexity" value={m.max_complexity ?? "–"} />
            <Metric label="Comment ratio" value={`${Math.round(m.comment_ratio * 100)}%`} />
            <Metric label="Findings" value={review.findings.length} />
          </div>
        </div>

        <div className="card p-5">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium"><Bot size={16} className="text-violet-300" /> AI summary</div>
          {review.ai_status === "pending" && <Spinner label="Claude is reviewing your code. This usually takes under a minute…" />}
          {review.ai_status === "skipped" && (
            <p className="text-sm text-ink-400">
              AI review was off for this submission. The static analysis results below are complete on their own.
            </p>
          )}
          {review.ai_status === "failed" && (
            <div className="flex items-start gap-2 text-sm text-sev-high">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              <span>AI review unavailable: {review.ai_error} Static analysis results are still shown below.</span>
            </div>
          )}
          {review.ai_status === "completed" && (
            <div className="space-y-3">
              <p className="text-sm leading-relaxed text-ink-300">{review.ai_summary}</p>
              {!!review.ai_strengths?.length && (
                <ul className="space-y-1">
                  {review.ai_strengths.map((s) => (
                    <li key={s} className="flex items-start gap-2 text-sm text-ink-300">
                      <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-brand-400" /> {s}
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-xs text-ink-400">AI findings are potential issues, not guaranteed defects. Review them before acting.</p>
            </div>
          )}
        </div>
      </div>

      {/* findings + code */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,420px)_1fr]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap gap-2">
            {(["all", "static", "ai"] as SourceFilter[]).map((s) => (
              <button key={s} onClick={() => setSource(s)}
                className={`rounded-md border px-2.5 py-1 text-xs transition ${source === s ? "border-brand-500/50 bg-brand-500/10 text-brand-400" : "border-ink-700 text-ink-400 hover:text-ink-100"}`}>
                {s === "all" ? `All · ${review.findings.length}` : s === "static"
                  ? <span className="flex items-center gap-1"><Cpu size={12} /> Static · {staticCount}</span>
                  : <span className="flex items-center gap-1"><Bot size={12} /> AI · {aiCount}</span>}
              </button>
            ))}
            <select value={severity} onChange={(e) => setSeverity(e.target.value as Severity | "all")}
              className="rounded-md border border-ink-700 bg-ink-850 px-2 py-1 text-xs text-ink-300 outline-none">
              <option value="all">All severities</option>
              {SEVERITIES.map((s) => <option key={s} value={s}>{s} ({review.finding_counts[s] ?? 0})</option>)}
            </select>
          </div>

          <div className="space-y-2 lg:max-h-[70vh] lg:overflow-y-auto lg:pr-1">
            {findings.length === 0 ? (
              <div className="card p-6 text-center text-sm text-ink-400">
                {review.findings.length === 0 ? "No issues found. Nice work." : "No findings match these filters."}
              </div>
            ) : findings.map((f) => (
              <FindingCard key={f.id} finding={f} active={!!f.line && f.line === focusLine} onSelect={setFocusLine} />
            ))}
          </div>
        </div>

        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-3 text-xs text-ink-400">
            {(["critical", "medium", "low"] as Severity[]).map((s) => (
              <span key={s} className="flex items-center gap-1.5">
                <span className={`h-2 w-2 rounded-full ${SEVERITY_STYLE[s].dot}`} />
                {s === "critical" ? "critical / high" : s === "low" ? "low / info" : s}
              </span>
            ))}
            <span>· click a finding to jump to its line</span>
          </div>
          <CodeEditor value={review.code} language={review.language} readOnly findings={review.findings} focusLine={focusLine} height="70vh" />
        </div>
      </div>

      {review.status === "completed" ? (
        <CorrectedCode review={review} />
      ) : (
        <div className="mt-8"><Spinner label="Corrected code will appear here when the AI review finishes…" /></div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-xs text-ink-400">{label}</div>
      <div className="font-medium tabular-nums">{value}</div>
    </div>
  );
}
