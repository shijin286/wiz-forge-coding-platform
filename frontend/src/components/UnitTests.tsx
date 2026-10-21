import { Bot, Check, Copy, Cpu, Download, FlaskConical } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ReviewDetail } from "../lib/types";
import CodeEditor from "./CodeEditor";
import { ErrorBox, Spinner, Tag } from "./ui";

type Tests = Awaited<ReturnType<typeof api.generateTests>>;

export default function UnitTests({ review }: { review: ReviewDetail }) {
  const [tests, setTests] = useState<Tests | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [aiConfigured, setAiConfigured] = useState(false);
  const [useAI, setUseAI] = useState(false);

  useEffect(() => {
    api.health().then((h) => { setAiConfigured(h.ai_configured); setUseAI(h.ai_configured); }).catch(() => {});
  }, []);

  const generate = async () => {
    setError("");
    setBusy(true);
    try {
      setTests(await api.generateTests(review.id, useAI));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate tests");
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!tests) return;
    try {
      await navigator.clipboard.writeText(tests.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard unavailable */ }
  };

  const download = () => {
    if (!tests) return;
    const url = URL.createObjectURL(new Blob([tests.code], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = tests.filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="mt-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold"><FlaskConical size={18} className="text-brand-400" /> Unit tests</h2>
          <p className="mt-1 text-sm text-ink-400">
            {aiConfigured
              ? "Generate a complete test file with Claude, or an instant skeleton from the code's public API."
              : "Generate a test skeleton from the code's public API. Add ANTHROPIC_API_KEY to get complete tests from Claude."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {aiConfigured && (
            <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-300">
              <input type="checkbox" checked={useAI} onChange={(e) => setUseAI(e.target.checked)} className="h-3.5 w-3.5 accent-emerald-500" />
              Use Claude
            </label>
          )}
          {tests && (
            <>
              <button className="btn-ghost px-3 py-1.5 text-xs" onClick={copy}>
                {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
              </button>
              <button className="btn-ghost px-3 py-1.5 text-xs" onClick={download}><Download size={13} /> {tests.filename}</button>
            </>
          )}
          <button className="btn-primary px-3 py-1.5 text-xs" onClick={generate} disabled={busy}>
            {busy ? "Generating…" : tests ? "Regenerate" : "Generate tests"}
          </button>
        </div>
      </div>

      {error && <ErrorBox message={error} />}
      {busy && useAI && <Spinner label="Claude is writing the tests. This can take up to a minute…" />}

      {tests && !busy && (
        <>
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-ink-400">
            {tests.source === "ai" ? <Tag tone="violet"><Bot size={12} /> Claude</Tag> : <Tag><Cpu size={12} /> Skeleton</Tag>}
            <Tag>{tests.framework}</Tag>
            <span>{tests.notes}</span>
          </div>
          <CodeEditor value={tests.code} language={review.language} readOnly height="50vh" />
        </>
      )}
    </section>
  );
}
