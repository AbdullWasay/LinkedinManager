"use client";

type Point = {
  date: string;
  label?: string;
  jobs_found: number;
  emails_sent: number;
};

const RANGES = [
  { key: "2h", label: "Last 2 hours" },
  { key: "24h", label: "Last 24 hours" },
  { key: "7d", label: "Last 7 days" },
  { key: "30d", label: "Last 30 days" },
] as const;

export function AnalyticsChart({
  title,
  series,
  metric,
  range,
  onRangeChange,
  color,
}: {
  title: string;
  series: Point[];
  metric: "jobs_found" | "emails_sent";
  range: string;
  onRangeChange: (range: string) => void;
  color: string;
}) {
  const width = 640;
  const height = 220;
  const padX = 36;
  const padY = 28;
  const values = series.map((p) => p[metric]);
  const max = Math.max(1, ...values);
  const step = series.length > 1 ? (width - padX * 2) / (series.length - 1) : 0;

  const points = series.map((p, i) => {
    const x = padX + i * step;
    const y = height - padY - (p[metric] / max) * (height - padY * 2);
    return { x, y, value: p[metric], label: p.label || p.date };
  });

  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const area =
    points.length > 0
      ? `${line} L${points[points.length - 1].x},${height - padY} L${points[0].x},${height - padY} Z`
      : "";

  return (
    <article className="surface rounded-2xl p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg text-[#0b3b3a]">{title}</h3>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Total in range: {values.reduce((a, b) => a + b, 0)}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {RANGES.map((r) => (
            <button
              key={r.key}
              type="button"
              className={`range-pill ${range === r.key ? "active" : ""}`}
              onClick={() => onRangeChange(r.key)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <svg width={width} height={height} role="img" className="max-w-full">
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const y = height - padY - t * (height - padY * 2);
            return (
              <g key={t}>
                <line x1={padX} x2={width - padX} y1={y} y2={y} stroke="#d7e8e5" strokeWidth="1" />
                <text x={8} y={y + 4} fontSize="10" fill="#456664" fontFamily="Poppins, sans-serif">
                  {Math.round(max * t)}
                </text>
              </g>
            );
          })}
          {area && <path d={area} fill={color} opacity="0.16" />}
          {line && <path d={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />}
          {points.map((p, i) => (
            <g key={`${p.label}-${i}`}>
              <circle cx={p.x} cy={p.y} r={p.value > 0 ? 4 : 2.5} fill={color} />
              {(i === 0 || i === points.length - 1 || i % Math.ceil(points.length / 6) === 0) && (
                <text
                  x={p.x}
                  y={height - 8}
                  textAnchor="middle"
                  fontSize="10"
                  fill="#456664"
                  fontFamily="Poppins, sans-serif"
                >
                  {p.label}
                </text>
              )}
            </g>
          ))}
        </svg>
      </div>
    </article>
  );
}
