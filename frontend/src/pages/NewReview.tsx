import { Bot, FileUp, Github, Info, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import CodeEditor from "../components/CodeEditor";
import { ErrorBox, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { LANGUAGE_LABEL, languageFromFilename } from "../lib/format";
import { SAMPLES } from "../lib/samples";

const MAX_CHARS = 100_000;

export default function NewReview() {
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState("");
  const [useAI, setUseAI] = useState(true);
  const [aiConfigured, setAiConfigured] = useState(true);

  useEffect(() => {
    api.health().then((h) => {
      setAiConfigured(h.ai_configured);
      if (!h.ai_configured) setUseAI(false);
    }).catch(() => {});
  }, []);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showGithub, setShowGithub] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [importing, setImporting] = useState(false);
  // once the user picks a language themselves, detection only suggests instead of switching
  const [languageChosen, setLanguageChosen] = useState(false);
  const [detected, setDetected] = useState<string | null>(null);

  useEffect(() => {
    if (code.trim().length < 20) {
      setDetected(null);
      return;
    }
    const t = setTimeout(() => {
      api.detectLanguage(code)
        .then(({ language: found }) => {
          setDetected(found);
          if (found && !languageChosen) setLanguage(found);
        })
        .catch(() => setDetected(null));
    }, 400);
    return () => clearTimeout(t);
  }, [code, languageChosen]);

  const chooseLanguage = (lang: string) => {
    setLanguage(lang);
    setLanguageChosen(true);
  };

  const loadSample = () => {
    const sample = SAMPLES[language] ?? SAMPLES.python;
    chooseLanguage(SAMPLES[language] ? language : "python");
    setTitle(sample.title);
    setCode(sample.code);
  };

  const importGithub = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setImporting(true);
    try {
      const file = await api.importFromGithub(githubUrl);
      setCode(file.code);
      if (file.language !== "other") chooseLanguage(file.language);
      else setLanguageChosen(false);
      // use the path inside the repository as the title, e.g. src/app.py
      const path = githubUrl.split(/\/blob\/[^/]+\/|githubusercontent\.com\/[^/]+\/[^/]+\/[^/]+\//)[1];
      setTitle(path || file.filename);
      setShowGithub(false);
      setGithubUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > MAX_CHARS * 4) {
      setError("File is too large to review.");
      return;
    }
    setCode(await file.text());
    const fromName = languageFromFilename(file.name);
    if (fromName !== "other") chooseLanguage(fromName);
    else setLanguageChosen(false); // unknown extension: let detection decide
    if (!title) setTitle(file.name);
  };

  const submit = async () => {
    setError("");
    setBusy(true);
    try {
      const review = await api.createReview({ title: title || "Untitled review", language, code, use_ai: useAI });
      navigate(`/review/${review.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
      setBusy(false);
    }
  };

  const tooLong = code.length > MAX_CHARS;

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="New review" subtitle="Paste code, upload a file or import one from GitHub. It is analysed, never executed." />

      <div className="card mb-4 grid gap-3 p-4 md:grid-cols-[1fr_180px_auto]">
        <input className="input" placeholder="Title, e.g. payment-service/handlers.py" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
        <select className="input" value={language} onChange={(e) => chooseLanguage(e.target.value)}>
          {Object.entries(LANGUAGE_LABEL).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
        <div className="flex gap-2">
          <button className="btn-ghost flex-1" onClick={() => fileInput.current?.click()}><FileUp size={15} /> Upload</button>
          <button className="btn-ghost flex-1" onClick={() => setShowGithub(!showGithub)}><Github size={15} /> GitHub</button>
          <button className="btn-ghost flex-1" onClick={loadSample}><Sparkles size={15} /> Sample</button>
          <input ref={fileInput} type="file" className="hidden" onChange={onFile}
            accept=".py,.js,.jsx,.mjs,.cjs,.ts,.tsx,.java,.c,.h,.cpp,.cc,.cxx,.hpp,.go,.txt" />
        </div>
        {showGithub && (
          <form className="flex flex-col gap-2 sm:flex-row md:col-span-3" onSubmit={importGithub}>
            <input className="input" type="url" required autoFocus value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/owner/repo/blob/main/src/app.py" />
            <button className="btn-primary shrink-0" disabled={importing}>{importing ? "Importing…" : "Import file"}</button>
          </form>
        )}
      </div>

      {detected && detected !== language && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-sev-medium/30 bg-sev-medium/10 px-3 py-2 text-sm text-sev-medium">
          <span className="flex items-center gap-2">
            <Info size={15} className="shrink-0" />
            This code looks like {LANGUAGE_LABEL[detected]}, but {LANGUAGE_LABEL[language]} is selected.
          </span>
          <button className="rounded-md border border-sev-medium/40 px-2.5 py-1 text-xs font-medium hover:bg-sev-medium/10"
            onClick={() => chooseLanguage(detected)}>
            Switch to {LANGUAGE_LABEL[detected]}
          </button>
        </div>
      )}

      <CodeEditor value={code} language={language} onChange={setCode} />

      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <label className="flex cursor-pointer items-center gap-3 text-sm text-ink-300">
          <input type="checkbox" checked={useAI} onChange={(e) => setUseAI(e.target.checked)}
            disabled={!aiConfigured} className="h-4 w-4 accent-emerald-500" />
          <span className="flex items-center gap-1.5"><Bot size={15} className="text-violet-300" /> Include AI review (Claude)</span>
          {!aiConfigured && (
            <span className="text-xs text-ink-400">Off: add ANTHROPIC_API_KEY to backend/.env to turn it on</span>
          )}
        </label>
        <div className="flex items-center gap-4">
          <span className={`text-xs tabular-nums ${tooLong ? "text-sev-critical" : "text-ink-400"}`}>
            {code.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} chars
          </span>
          <button className="btn-primary" disabled={busy || !code.trim() || tooLong} onClick={submit}>
            {busy ? "Analysing…" : "Run review"}
          </button>
        </div>
      </div>
      {error && <div className="mt-4"><ErrorBox message={error} /></div>}
    </div>
  );
}
