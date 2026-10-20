import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { SEVERITY_STYLE, scoreColor } from "../lib/format";
import type { Severity } from "../lib/types";

export function SeverityBadge({ severity }: { severity: Severity }) {
  const s = SEVERITY_STYLE[severity];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium capitalize ${s.bg} ${s.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {severity}
    </span>
  );
}

export function Tag({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "brand" | "violet" }) {
  const tones = {
    neutral: "border-ink-700 text-ink-300",
    brand: "border-brand-500/30 bg-brand-500/10 text-brand-400",
    violet: "border-violet-400/30 bg-violet-400/10 text-violet-300",
  };
  return <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs ${tones[tone]}`}>{children}</span>;
}

export function ScoreRing({ score, grade, size = 120 }: { score: number; grade: string; size?: number }) {
  const stroke = size / 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = scoreColor(score);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-ink-700)" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)}
          style={{ transition: "stroke-dashoffset 600ms ease" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="text-3xl font-semibold tabular-nums" style={{ fontSize: size / 4 }}>{score}</div>
          <div className="text-xs text-ink-400">Grade <span style={{ color }} className="font-semibold">{grade}</span></div>
        </div>
      </div>
    </div>
  );
}

export function GradePill({ grade, score }: { grade: string; score: number }) {
  const color = scoreColor(score);
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums"
      style={{ color, background: `${color}1a` }}>
      {grade} · {score}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-ink-400">
      <Loader2 size={16} className="animate-spin" /> {label}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-400">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return <div className="rounded-lg border border-sev-critical/30 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">{message}</div>;
}
