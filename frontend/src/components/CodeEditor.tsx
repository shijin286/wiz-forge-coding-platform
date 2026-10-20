import Editor, { type OnMount } from "@monaco-editor/react";
import { useEffect, useRef } from "react";
import { MONACO_LANGUAGE } from "../lib/format";
import type { Finding } from "../lib/types";

type MonacoEditor = Parameters<OnMount>[0];
type Monaco = Parameters<OnMount>[1];

interface Props {
  value: string;
  language: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  findings?: Finding[];
  focusLine?: number | null;
  height?: string | number;
}

export default function CodeEditor({ value, language, onChange, readOnly, findings = [], focusLine, height = "60vh" }: Props) {
  const editorRef = useRef<MonacoEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const decorations = useRef<string[]>([]);

  const applyDecorations = () => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco) return;
    const byLine = new Map<number, Finding>();
    const rank = ["critical", "high", "medium", "low", "info"];
    for (const f of findings) {
      if (!f.line) continue;
      const prev = byLine.get(f.line);
      if (!prev || rank.indexOf(f.severity) < rank.indexOf(prev.severity)) byLine.set(f.line, f);
    }
    const next = [...byLine.entries()].map(([line, f]) => ({
      range: new monaco.Range(line, 1, line, 1),
      options: {
        isWholeLine: true,
        className: `cg-line-${f.severity}${line === focusLine ? " cg-line-focus" : ""}`,
        glyphMarginClassName: `cg-glyph-${f.severity}`,
        hoverMessage: { value: `**${f.title}** (${f.severity})` },
      },
    }));
    decorations.current = editor.deltaDecorations(decorations.current, next);
  };

  useEffect(applyDecorations, [findings, focusLine]);

  useEffect(() => {
    if (focusLine && editorRef.current) editorRef.current.revealLineInCenter(focusLine);
  }, [focusLine]);

  const onMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    monaco.editor.defineTheme("wizforge", {
      base: "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": "#0f141b",
        "editor.lineHighlightBackground": "#1a212c",
        "editorGutter.background": "#0f141b",
        "editorLineNumber.foreground": "#3a4659",
      },
    });
    monaco.editor.setTheme("wizforge");
    applyDecorations();
  };

  return (
    <div className="overflow-hidden rounded-xl border border-ink-700/70">
      <Editor
        height={height}
        language={MONACO_LANGUAGE[language] ?? "plaintext"}
        value={value}
        onChange={(v) => onChange?.(v ?? "")}
        onMount={onMount}
        theme="vs-dark"
        loading={<div className="p-4 text-sm text-ink-400">Loading editor…</div>}
        options={{
          readOnly,
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 13,
          minimap: { enabled: false },
          glyphMargin: findings.length > 0,
          scrollBeyondLastLine: false,
          padding: { top: 12 },
          renderLineHighlight: readOnly ? "none" : "line",
          automaticLayout: true,
          tabSize: 4,
        }}
      />
    </div>
  );
}
