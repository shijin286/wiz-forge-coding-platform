import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { Stats } from "../lib/types";

// Validated against the dark card surface (#0f141b): OKLCH L 0.48-0.67, chroma >= 0.1, contrast >= 3:1
const LINE = "#059669";
const SURFACE = "var(--color-ink-900)";

const H = 200;
const PAD = { top: 16, right: 40, bottom: 26, left: 34 };

export default function ScoreTrend({ points }: { points: Stats["score_trend"] }) {
  const navigate = useNavigate();
  const svgRef = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  // draw at the container's real pixel width so text and markers keep a constant size
  const boxRef = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(640);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setW(Math.max(280, Math.round(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [showTable]);

  const geo = useMemo(() => {
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const step = points.length > 1 ? innerW / (points.length - 1) : 0;
    const xy = points.map((p, i) => ({
      ...p,
      x: PAD.left + (points.length > 1 ? i * step : innerW / 2),
      y: PAD.top + innerH * (1 - p.score / 100),
    }));
    return { xy, innerH };
  }, [points, W]);

  if (points.length < 2) return null;

  const path = geo.xy.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const last = geo.xy[geo.xy.length - 1];
  const active = hover != null ? geo.xy[hover] : null;
  const change = last.score - geo.xy[0].score;

  const onMove = (e: MouseEvent<SVGRectElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * W;
    let nearest = 0;
    geo.xy.forEach((p, i) => { if (Math.abs(p.x - x) < Math.abs(geo.xy[nearest].x - x)) nearest = i; });
    setHover(nearest);
  };

  return (
    <div className="card p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-sm font-medium">Quality score over time</h2>
          <p className="text-xs text-ink-400">
            Last {points.length} reviews · {change === 0 ? "no change" : `${change > 0 ? "+" : ""}${change} points`} from first to latest
          </p>
        </div>
        <button className="text-xs text-ink-400 underline-offset-2 hover:text-ink-100 hover:underline"
          onClick={() => setShowTable(!showTable)}>
          {showTable ? "Show chart" : "Show as table"}
        </button>
      </div>

      {showTable ? (
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-ink-400">
            <tr><th className="py-1.5 font-medium">Review</th><th className="py-1.5 text-right font-medium">Score</th></tr>
          </thead>
          <tbody className="divide-y divide-ink-700/70">
            {points.map((p) => (
              <tr key={p.id}><td className="py-1.5 text-ink-300">{p.title}</td><td className="py-1.5 text-right tabular-nums">{p.score}</td></tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div ref={boxRef} className="relative">
          <svg ref={svgRef} width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block" role="img"
            aria-label={`Quality score over the last ${points.length} reviews, from ${geo.xy[0].score} to ${last.score}`}>
            {/* recessive grid: 0 / 50 / 100 */}
            {[0, 50, 100].map((v) => {
              const y = PAD.top + geo.innerH * (1 - v / 100);
              return (
                <g key={v}>
                  <line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} stroke="var(--color-ink-700)" strokeWidth={1}
                    strokeDasharray={v === 0 ? undefined : "2 4"} />
                  <text x={PAD.left - 8} y={y + 3.5} textAnchor="end" fontSize={11} fill="var(--color-ink-400)">{v}</text>
                </g>
              );
            })}
            <text x={PAD.left} y={H - 6} fontSize={11} fill="var(--color-ink-400)">oldest</text>
            <text x={W - PAD.right} y={H - 6} fontSize={11} fill="var(--color-ink-400)" textAnchor="end">latest</text>

            {active && (
              <line x1={active.x} x2={active.x} y1={PAD.top} y2={PAD.top + geo.innerH}
                stroke="var(--color-ink-600)" strokeWidth={1} />
            )}

            <path d={path} fill="none" stroke={LINE} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            {geo.xy.map((p, i) => (
              <circle key={p.id} cx={p.x} cy={p.y} r={hover === i ? 5.5 : 4} fill={LINE}
                stroke={SURFACE} strokeWidth={2} />
            ))}

            {/* direct label on the latest point only */}
            <text x={last.x + 9} y={last.y + 4} fontSize={12} fontWeight={600} fill="var(--color-ink-100)">{last.score}</text>

            {/* hit area larger than the marks */}
            <rect x={PAD.left - 12} y={0} width={W - PAD.left - PAD.right + 24} height={H} fill="transparent"
              className="cursor-pointer" onMouseMove={onMove} onMouseLeave={() => setHover(null)}
              onClick={() => active && navigate(`/review/${active.id}`)} />
          </svg>

          {active && (
            <div className="pointer-events-none absolute z-10 rounded-lg border border-ink-700 bg-ink-850 px-2.5 py-1.5 text-xs shadow-lg"
              style={{
                left: `${(active.x / W) * 100}%`,
                top: `${(active.y / H) * 100}%`,
                // keep the tooltip inside the card near the left and right edges
                transform: `translate(${active.x / W < 0.2 ? "-12px" : active.x / W > 0.8 ? "calc(-100% + 12px)" : "-50%"}, calc(-100% - 10px))`,
              }}>
              <div className="max-w-[220px] truncate font-medium text-ink-100">{active.title}</div>
              <div className="text-ink-400">Score <span className="tabular-nums text-ink-100">{active.score}</span> · click to open</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
