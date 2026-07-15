"use client";

export type PaymentTrendPoint = {
  due_date: string;
  days_past_due: number;
  status: string;
};

type Props = {
  payments: PaymentTrendPoint[];
};

function formatCycleDate(iso: string) {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
}

function dpdTone(dpd: number): "low" | "medium" | "high" | "critical" {
  if (dpd >= 30) return "critical";
  if (dpd >= 15) return "high";
  if (dpd >= 1) return "medium";
  return "low";
}

const TONE_COLOR: Record<string, string> = {
  low: "#166534",
  medium: "#a16207",
  high: "#b45309",
  critical: "#9b1c1c",
};

const TONE_BG: Record<string, string> = {
  low: "#dcfce7",
  medium: "#fef3c7",
  high: "#ffedd5",
  critical: "#fde8e8",
};

export function DpdTrendChart({ payments }: Props) {
  const sorted = [...payments].sort((a, b) => a.due_date.localeCompare(b.due_date));
  const recent = sorted.slice(-6);

  if (!recent.length) {
    return <p className="muted" style={{ margin: 0 }}>No payment history to chart.</p>;
  }

  const maxDpd = Math.max(...recent.map((p) => p.days_past_due), 30);
  const yMax = Math.ceil(maxDpd / 10) * 10 || 10;
  const first = recent[0].days_past_due;
  const last = recent[recent.length - 1].days_past_due;
  const delta = last - first;
  const trendLabel =
    delta > 5 ? "Worsening" : delta < -5 ? "Improving" : "Stable";
  const trendClass =
    delta > 5 ? "dpd-trend-badge worsening" : delta < -5 ? "dpd-trend-badge improving" : "dpd-trend-badge stable";

  const W = 640;
  const H = 220;
  const pad = { top: 28, right: 20, bottom: 44, left: 44 };
  const chartW = W - pad.left - pad.right;
  const chartH = H - pad.top - pad.bottom;
  const step = recent.length > 1 ? chartW / (recent.length - 1) : 0;

  const points = recent.map((p, i) => {
    const x = pad.left + (recent.length > 1 ? i * step : chartW / 2);
    const y = pad.top + chartH - (p.days_past_due / yMax) * chartH;
    return { x, y, ...p };
  });

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${(pad.top + chartH).toFixed(1)} L ${points[0].x.toFixed(1)} ${(pad.top + chartH).toFixed(1)} Z`;

  const yTicks = [0, 15, 30].filter((t) => t <= yMax);
  if (!yTicks.includes(yMax) && yMax > 30) yTicks.push(yMax);

  return (
    <div className="dpd-chart-card" data-testid="dpd-trend-chart">
      <div className="dpd-chart-header">
        <div>
          <div className="stat-label">Latest DPD</div>
          <div className="dpd-chart-latest">
            <span className={`dpd-pill dpd-pill-${dpdTone(last)}`}>{last} days</span>
            <span className="muted" style={{ fontSize: "0.85rem" }}>
              {formatCycleDate(recent[recent.length - 1].due_date)}
            </span>
          </div>
        </div>
        <div className="dpd-chart-header-right">
          <span className={trendClass}>{trendLabel}</span>
          <span className="muted mono" style={{ fontSize: "0.8rem" }}>
            {first} → {last} over {recent.length} cycles
          </span>
        </div>
      </div>

      <div className="dpd-chart-svg-wrap">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="dpd-chart-svg"
          role="img"
          aria-label="Days past due trend chart"
        >
          <defs>
            <linearGradient id="dpdAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0b6e4f" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#0b6e4f" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* threshold bands */}
          {yMax >= 30 && (
            <rect
              x={pad.left}
              y={pad.top}
              width={chartW}
              height={Math.max(0, (1 - 30 / yMax) * chartH)}
              fill="#fde8e8"
              opacity={0.35}
            />
          )}
          {yMax >= 15 && (
            <rect
              x={pad.left}
              y={pad.top + Math.max(0, (1 - 30 / yMax) * chartH)}
              width={chartW}
              height={Math.max(0, ((Math.min(30, yMax) - 15) / yMax) * chartH)}
              fill="#ffedd5"
              opacity={0.35}
            />
          )}

          {/* grid */}
          {yTicks.map((tick) => {
            const y = pad.top + chartH - (tick / yMax) * chartH;
            return (
              <g key={tick}>
                <line
                  x1={pad.left}
                  y1={y}
                  x2={pad.left + chartW}
                  y2={y}
                  stroke="var(--line)"
                  strokeDasharray={tick === 0 ? "0" : "4 4"}
                  strokeWidth={1}
                />
                <text x={pad.left - 8} y={y + 4} textAnchor="end" className="dpd-axis-label">
                  {tick}
                </text>
              </g>
            );
          })}

          {/* 15 / 30 reference labels */}
          {yMax >= 15 && (
            <text x={pad.left + chartW + 4} y={pad.top + chartH - (15 / yMax) * chartH + 3} className="dpd-ref-label">
              Watch 15
            </text>
          )}
          {yMax >= 30 && (
            <text x={pad.left + chartW + 4} y={pad.top + chartH - (30 / yMax) * chartH + 3} className="dpd-ref-label">
              High 30
            </text>
          )}

          <path d={areaPath} fill="url(#dpdAreaGrad)" />
          <path d={linePath} fill="none" stroke="#0b6e4f" strokeWidth={2.5} strokeLinejoin="round" />

          {points.map((p) => {
            const tone = dpdTone(p.days_past_due);
            return (
              <g key={p.due_date}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={7}
                  fill={TONE_BG[tone]}
                  stroke={TONE_COLOR[tone]}
                  strokeWidth={2}
                />
                <text x={p.x} y={p.y - 12} textAnchor="middle" className="dpd-point-label">
                  {p.days_past_due}
                </text>
                <text x={p.x} y={pad.top + chartH + 22} textAnchor="middle" className="dpd-axis-label">
                  {formatCycleDate(p.due_date)}
                </text>
                <title>{`${formatCycleDate(p.due_date)}: ${p.days_past_due} DPD (${p.status})`}</title>
              </g>
            );
          })}

          <text x={pad.left} y={H - 6} className="dpd-axis-title">
            EMI cycle
          </text>
          <text
            x={14}
            y={pad.top + chartH / 2}
            transform={`rotate(-90 14 ${pad.top + chartH / 2})`}
            className="dpd-axis-title"
          >
            Days past due
          </text>
        </svg>
      </div>

      <div className="dpd-legend">
        <span><i className="dpd-legend-dot low" /> On time (0)</span>
        <span><i className="dpd-legend-dot medium" /> Watch (1–14)</span>
        <span><i className="dpd-legend-dot high" /> Elevated (15–29)</span>
        <span><i className="dpd-legend-dot critical" /> Critical (30+)</span>
      </div>
    </div>
  );
}
