import { ArrowRight, FilePlus2, Gauge, ListChecks, ShieldAlert } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import ScoreTrend from "../components/ScoreTrend";
import { ErrorBox, GradePill, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { LANGUAGE_LABEL, SEVERITIES, SEVERITY_STYLE, scoreColor, timeAgo } from "../lib/format";
import type { Stats } from "../lib/types";

function StatCard({ icon, label, value, hint }: { icon: ReactNode; label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-sm text-ink-400">{icon}{label}</div>
      <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-400">{hint}</div>}
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.stats().then(setStats).catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorBox message={error} />;
  if (!stats) return <Spinner label="Loading dashboard…" />;

  const securityCount = stats.by_category.security ?? 0;
  const maxSeverity = Math.max(1, ...SEVERITIES.map((s) => stats.by_severity[s] ?? 0));

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title={`Hi, ${user?.name.split(" ")[0]}`}
        subtitle="An overview of your code reviews."
        action={<Link to="/review/new" className="btn-primary"><FilePlus2 size={16} /> New review</Link>}
      />

      {stats.total_reviews === 0 ? (
        <div className="card flex flex-col items-center gap-4 px-6 py-16 text-center">
          <div className="grid h-12 w-12 place-items-center rounded-xl bg-brand-500/10 text-brand-400"><ListChecks size={22} /></div>
          <div>
            <h2 className="text-lg font-semibold">No reviews yet</h2>
            <p className="mt-1 max-w-sm text-sm text-ink-400">Paste or upload a file to get a quality score, static-analysis findings and an AI review.</p>
          </div>
          <Link to="/review/new" className="btn-primary">Start your first review</Link>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard icon={<ListChecks size={15} />} label="Reviews" value={stats.total_reviews} />
            <StatCard
              icon={<Gauge size={15} />} label="Average score"
              value={<span style={{ color: scoreColor(stats.average_score ?? 0) }}>{stats.average_score ?? "–"}</span>}
              hint="out of 100"
            />
            <StatCard icon={<ShieldAlert size={15} />} label="Security findings" value={securityCount} />
            <StatCard
              icon={<span className="h-2 w-2 rounded-full bg-sev-critical" />} label="Critical + high"
              value={(stats.by_severity.critical ?? 0) + (stats.by_severity.high ?? 0)}
            />
          </div>

          <ScoreTrend points={stats.score_trend} />

          <div className="grid gap-6 lg:grid-cols-5">
            <div className="card p-5 lg:col-span-2">
              <h2 className="text-sm font-medium">Findings by severity</h2>
              <p className="text-xs text-ink-400">{stats.total_findings} total across all reviews</p>
              <div className="mt-5 space-y-3">
                {SEVERITIES.map((s) => {
                  const n = stats.by_severity[s] ?? 0;
                  return (
                    <div key={s} className="grid grid-cols-[72px_1fr_36px] items-center gap-3 text-sm">
                      <span className={`capitalize ${SEVERITY_STYLE[s].text}`}>{s}</span>
                      <div className="h-2 overflow-hidden rounded-full bg-ink-800">
                        <div className={`h-full rounded-full ${SEVERITY_STYLE[s].dot}`} style={{ width: `${(n / maxSeverity) * 100}%` }} />
                      </div>
                      <span className="text-right tabular-nums text-ink-300">{n}</span>
                    </div>
                  );
                })}
              </div>

              <h2 className="mt-8 text-sm font-medium">Languages</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(stats.by_language).map(([lang, n]) => (
                  <span key={lang} className="rounded-md border border-ink-700 px-2 py-1 text-xs text-ink-300">
                    {LANGUAGE_LABEL[lang] ?? lang} <span className="text-ink-400">· {n}</span>
                  </span>
                ))}
              </div>
            </div>

            <div className="card p-5 lg:col-span-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium">Recent reviews</h2>
                <Link to="/history" className="flex items-center gap-1 text-xs text-brand-400 hover:underline">View all <ArrowRight size={12} /></Link>
              </div>
              <ul className="mt-3 divide-y divide-ink-700/70">
                {stats.recent.map((r) => (
                  <li key={r.id}>
                    <Link to={`/review/${r.id}`} className="-mx-2 flex items-center justify-between gap-3 rounded-lg px-2 py-3 hover:bg-ink-850">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{r.title}</div>
                        <div className="text-xs text-ink-400">{LANGUAGE_LABEL[r.language]} · {timeAgo(r.created_at)}</div>
                      </div>
                      <div className="flex shrink-0 items-center gap-3">
                        <div className="hidden gap-1 sm:flex">
                          {SEVERITIES.filter((s) => r.finding_counts[s]).slice(0, 3).map((s) => (
                            <span key={s} className={`rounded px-1.5 text-xs tabular-nums ${SEVERITY_STYLE[s].bg} ${SEVERITY_STYLE[s].text}`}>
                              {r.finding_counts[s]}
                            </span>
                          ))}
                        </div>
                        {r.status === "processing" ? <Spinner /> : <GradePill grade={r.grade} score={r.quality_score} />}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
