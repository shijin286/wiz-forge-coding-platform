import { DiffEditor } from "@monaco-editor/react";
import { ArrowRight, Bot, Check, Copy, Cpu, Download, Wrench } from "lucide-react";
import { useState } from "react";
import { MONACO_LANGUAGE } from "../lib/format";
import type { ReviewDetail } from "../lib/types";
import { GradePill, Tag } from "./ui";

const EXTENSION: Record<string, string> = {
  python: "py", javascript: "js", typescript: "ts", java: "java", cpp: "cpp", c: "c", go: "go", other: "txt",
};

function downloadName(title: string, language: string): string {
  const base = (title.split("/").pop() || "code").replace(/\.[^.]+$/, "") || "code";
  return `${base}.fixed.${EXTENSION[language] ?? "txt"}`;
}

export default function CorrectedCode({ review }: { review: ReviewDetail }) {
  const [copied, setCopied] = useState(false);
  const [sideBySide, setSideBySide] = useState(true);
  const fixed = review.fixed_code;

  if (fixed == null) return null;

  const applied = review.fixes_applied ?? [];
  const remaining = review.fixes_remaining ?? [];
  const unchanged = fixed === review.code;
  const isAI = review.fixed_source === "ai";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(fixed);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard unavailable */ }
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([fixed], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadName(review.title, review.language);
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="mt-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold"><Wrench size={18} className="text-brand-400" /> Corrected code</h2>
          <p className="mt-1 text-sm text-ink-400">
            {unchanged
              ? "No automatic changes were needed."
              : isAI
                ? "Rewritten by Claude to resolve the findings. Review the changes before using them."
                : "Safe, mechanical fixes applied automatically. Issues that need judgement are listed below."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isAI ? <Tag tone="violet"><Bot size={12} /> AI fix</Tag> : <Tag><Cpu size={12} /> Auto-fix</Tag>}
          {review.fixed_score != null && review.fixed_grade && !unchanged && (
            <span className="flex items-center gap-1.5 text-xs text-ink-400">
              <GradePill grade={review.grade} score={review.quality_score} />
              <ArrowRight size={12} />
              <GradePill grade={review.fixed_grade} score={review.fixed_score} />
            </span>
          )}
          <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setSideBySide(!sideBySide)}>
            {sideBySide ? "Inline view" : "Side by side"}
          </button>
          <button className="btn-ghost px-3 py-1.5 text-xs" onClick={copy}>
            {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
          </button>
          <button className="btn-ghost px-3 py-1.5 text-xs" onClick={download}><Download size={13} /> Download</button>
        </div>
      </div>

      {!unchanged && (
        <div className="overflow-hidden rounded-xl border border-ink-700/70">
          {/* Monaco switches to inline view on narrow screens, so a colour legend reads correctly in both modes */}
          <div className="flex flex-wrap gap-4 border-b border-ink-700/70 bg-ink-900 px-3 py-1.5 text-xs text-ink-400">
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-sev-critical/60" /> Original (removed)</span>
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-brand-500/60" /> Corrected (added)</span>
          </div>
          <DiffEditor
            height="60vh"
            language={MONACO_LANGUAGE[review.language] ?? "plaintext"}
            original={review.code}
            modified={fixed}
            theme="vs-dark"
            // let @monaco-editor/react dispose the models itself; avoids "TextModel got disposed" on unmount
            keepCurrentOriginalModel
            keepCurrentModifiedModel
            loading={<div className="p-4 text-sm text-ink-400">Loading diff…</div>}
            options={{
              readOnly: true,
              renderSideBySide: sideBySide,
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              automaticLayout: true,
              renderOverviewRuler: false,
            }}
          />
        </div>
      )}

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-2 text-sm font-medium text-brand-400">Fixed ({applied.length})</h3>
          {applied.length === 0 ? (
            <p className="text-sm text-ink-400">Nothing could be fixed automatically.</p>
          ) : (
            <ul className="space-y-1.5 text-sm text-ink-300">
              {applied.map((a, i) => (
                <li key={i} className="flex items-start gap-2">
                  <Check size={14} className="mt-0.5 shrink-0 text-brand-400" />
                  <span>{a.line ? <span className="font-mono text-xs text-ink-400">line {a.line} · </span> : null}{a.description}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card p-4">
          <h3 className="mb-2 text-sm font-medium text-sev-medium">Still needs a manual fix ({remaining.length})</h3>
          {remaining.length === 0 ? (
            <p className="text-sm text-ink-400">Nothing left. The corrected code passes every static check.</p>
          ) : (
            <>
              <ul className="space-y-1.5 text-sm text-ink-300">
                {remaining.map((r, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sev-medium" />
                    <span>{r.line ? <span className="font-mono text-xs text-ink-400">line {r.line} · </span> : null}{r.title}</span>
                  </li>
                ))}
              </ul>
              {!isAI && (
                <p className="mt-3 text-xs text-ink-400">
                  These need a decision about intent. See each finding's suggested fix above, or enable the AI review to get a full rewrite.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
