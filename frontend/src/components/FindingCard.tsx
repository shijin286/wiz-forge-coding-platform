import { Bot, ChevronDown, Cpu, Lightbulb } from "lucide-react";
import { useState } from "react";
import type { Finding } from "../lib/types";
import { SeverityBadge, Tag } from "./ui";

interface Props {
  finding: Finding;
  active: boolean;
  onSelect: (line: number | null) => void;
}

export default function FindingCard({ finding: f, active, onSelect }: Props) {
  const [open, setOpen] = useState(false);
  const isAI = f.source === "ai";

  return (
    <div
      className={`rounded-lg border bg-ink-850 transition ${active ? "border-brand-500/60" : "border-ink-700/70 hover:border-ink-600"}`}
    >
      <button
        className="flex w-full items-start gap-3 p-3 text-left"
        onClick={() => {
          setOpen(!open);
          onSelect(f.line);
        }}
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={f.severity} />
            <span className="text-sm font-medium">{f.title}</span>
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-ink-400">
            {isAI ? (
              <Tag tone="violet"><Bot size={12} /> AI · {f.confidence} confidence</Tag>
            ) : (
              <Tag><Cpu size={12} /> Static · {f.rule_id}</Tag>
            )}
            <span className="capitalize">{f.category}</span>
            {f.line && <span className="font-mono">line {f.line}</span>}
          </div>
        </div>
        <ChevronDown size={16} className={`mt-1 shrink-0 text-ink-400 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="space-y-3 border-t border-ink-700/70 px-3 pb-3 pt-3 text-sm">
          <p className="leading-relaxed text-ink-300">{f.message}</p>
          {f.suggestion && (
            <div className="rounded-md border border-brand-500/20 bg-brand-500/5 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-brand-400">
                <Lightbulb size={13} /> Suggested fix
              </div>
              <p className="whitespace-pre-wrap leading-relaxed text-ink-300">{f.suggestion}</p>
            </div>
          )}
          {isAI && (
            <p className="text-xs text-ink-400">
              Potential issue identified by AI. Verify before acting on it.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
