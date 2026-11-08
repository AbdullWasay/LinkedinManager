"use client";

import { useMemo, useState } from "react";

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
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const values = useMemo(() => series.map((p) => Number(p[metric] || 0)), [series, metric]);
  const total = values.reduce((a, b) => a + b, 0);
  const max = Math.max(1, ...values, 0);
  const step = series.length > 1 ? (width - padX * 2) / (series.length - 1) : 0;

  const points = series.map((p, i) => {
    const value = Number(p[metric] || 0);
    const x = series.length === 1 ? width / 2 : padX + i * step;
    const y = height - padY - (value / max) * (height - padY * 2);
    return { x, y, value, label: p.label || p.date, date: p.date };
  });

  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const area =
    points.length > 0
      ? `${line} L${points[points.length - 1].x},${height - padY} L${points[0].x},${height - padY} Z`
      : "";

  const hovered = hoverIndex != null ? points[hoverIndex] : null;
  const metricLabel = metric === "emails_sent" ? "emails sent" : "jobs found";

  return (
    <article className="surface rounded-2xl p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg text-[#0b3b3a]">{title}</h3>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Total in range: {total}</p>
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

      <div className="relative mt-4 overflow-x-auto">
        {series.length === 0 ? (
          <p className="py-16 text-center text-sm text-[var(--text-muted)]">No data for this range yet.</p>
        ) : (
          <svg
            width={width}
            height={height}
            role="img"
            aria-label={`${title} chart`}
            className="max-w-full"
            onMouseLeave={() => setHoverIndex(null)}
          >
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
            {line && (
              <path d={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
            )}
            {points.map((p, i) => (
              <g key={`${p.date}-${i}`}>
                {/* Wide hit target for hover */}
                <rect
                  x={p.x - Math.max(12, step / 2)}
                  y={padY - 8}
                  width={Math.max(24, step)}
                  height={height - padY * 2 + 16}
                  fill="transparent"
                  onMouseEnter={() => setHoverIndex(i)}
                />
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={hoverIndex === i ? 6 : p.value > 0 ? 4.5 : 2.5}
                  fill={color}
                  stroke="#fff"
                  strokeWidth={hoverIndex === i ? 2 : 0}
                />
                {p.value > 0 && (
                  <text
                    x={p.x}
                    y={Math.max(padY - 4, p.y - 10)}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight="600"
                    fill="#0b3b3a"
                    fontFamily="Poppins, sans-serif"
                    opacity={hoverIndex === i || p.value === max ? 1 : 0.7}
                  >
                    {p.value}
                  </text>
                )}
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
            {hovered && (
              <g pointerEvents="none">
                <line
                  x1={hovered.x}
                  x2={hovered.x}
                  y1={padY}
                  y2={height - padY}
                  stroke={color}
                  strokeDasharray="4 4"
                  opacity="0.45"
                />
                {(() => {
                  const boxW = 148;
                  const boxH = 44;
                  const boxX = Math.min(Math.max(hovered.x - boxW / 2, 8), width - boxW - 8);
                  const boxY = Math.max(8, hovered.y - boxH - 14);
                  return (
                    <>
                      <rect
                        x={boxX}
                        y={boxY}
                        width={boxW}
                        height={boxH}
                        rx={10}
                        fill="#0b3b3a"
                        opacity="0.95"
                      />
                      <text
                        x={boxX + 12}
                        y={boxY + 18}
                        fontSize="11"
                        fill="#cde8e4"
                        fontFamily="Poppins, sans-serif"
                      >
                        {hovered.label}
                      </text>
                      <text
                        x={boxX + 12}
                        y={boxY + 34}
                        fontSize="12"
                        fontWeight="600"
                        fill="#ffffff"
                        fontFamily="Poppins, sans-serif"
                      >
                        {hovered.value} {metricLabel}
                      </text>
                    </>
                  );
                })()}
              </g>
            )}
          </svg>
        )}
      </div>
    </article>
  );
}
