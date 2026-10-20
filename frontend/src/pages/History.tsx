import { Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorBox, GradePill, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { LANGUAGE_LABEL, SEVERITIES, SEVERITY_STYLE, timeAgo } from "../lib/format";
import type { ReviewSummary } from "../lib/types";

const PAGE_SIZE = 15;

export default function History() {
  const [items, setItems] = useState<ReviewSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [language, setLanguage] = useState("");
  const [page, setPage] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      api.listReviews({ search, language, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
        .then((r) => { setItems(r.items); setTotal(r.total); })
        .catch((e) => setError(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [search, language, page]);

  const remove = async (id: number) => {
    if (!confirm("Delete this review? This cannot be undone.")) return;
    await api.deleteReview(id);
    setItems((prev) => prev?.filter((r) => r.id !== id) ?? null);
    setTotal((t) => t - 1);
  };

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Review history" subtitle={`${total} review${total === 1 ? "" : "s"}`} />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
          <input className="input pl-9" placeholder="Search by title" value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }} />
        </div>
        <select className="input sm:w-48" value={language} onChange={(e) => { setLanguage(e.target.value); setPage(0); }}>
          <option value="">All languages</option>
          {Object.entries(LANGUAGE_LABEL).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </div>

      {error && <ErrorBox message={error} />}
      {!items ? <Spinner label="Loading…" /> : items.length === 0 ? (
        <div className="card p-10 text-center text-sm text-ink-400">
          No reviews found. <Link to="/review/new" className="text-brand-400 hover:underline">Create one</Link>.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="border-b border-ink-700/70 text-left text-xs text-ink-400">
                <tr>
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium">Language</th>
                  <th className="px-4 py-3 font-medium">Findings</th>
                  <th className="px-4 py-3 font-medium">Score</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-700/70">
                {items.map((r) => (
                  <tr key={r.id} className="hover:bg-ink-850">
                    <td className="max-w-xs px-4 py-3">
                      <Link to={`/review/${r.id}`} className="block truncate font-medium hover:text-brand-400">{r.title}</Link>
                    </td>
                    <td className="px-4 py-3 text-ink-300">{LANGUAGE_LABEL[r.language]}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        {SEVERITIES.filter((s) => r.finding_counts[s]).map((s) => (
                          <span key={s} title={s} className={`rounded px-1.5 text-xs tabular-nums ${SEVERITY_STYLE[s].bg} ${SEVERITY_STYLE[s].text}`}>
                            {r.finding_counts[s]}
                          </span>
                        ))}
                        {Object.keys(r.finding_counts).length === 0 && <span className="text-xs text-ink-400">none</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {r.status === "processing" ? <Spinner /> : <GradePill grade={r.grade} score={r.quality_score} />}
                    </td>
                    <td className="px-4 py-3 text-ink-400">{timeAgo(r.created_at)}</td>
                    <td className="px-2 py-3">
                      <button onClick={() => remove(r.id)} className="rounded-md p-1.5 text-ink-400 hover:bg-ink-800 hover:text-sev-critical" title="Delete">
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {pages > 1 && (
            <div className="flex items-center justify-between border-t border-ink-700/70 px-4 py-3 text-sm text-ink-400">
              <span>Page {page + 1} of {pages}</span>
              <div className="flex gap-2">
                <button className="btn-ghost px-3 py-1" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
                <button className="btn-ghost px-3 py-1" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
