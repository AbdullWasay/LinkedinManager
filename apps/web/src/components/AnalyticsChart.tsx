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

// High-contrast on the light teal dashboard: navy + amber (not teal-on-teal).
const EMAIL_COLOR = "#1e3a8a";
const EMAIL_LABEL = "#93c5fd";
const JOBS_COLOR = "#c2410c";
const JOBS_LABEL = "#fdba74";

export function AnalyticsChart({
  series,
  range,
  onRangeChange,
}: {
  series: Point[];
  range: string;
  onRangeChange: (range: string) => void;
}) {
  const width = 960;
  const height = 280;
  const padX = 44;
  const padY = 32;
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const emailValues = useMemo(
    () => series.map((p) => Number(p.emails_sent || 0)),
    [series]
  );
  const jobValues = useMemo(() => series.map((p) => Number(p.jobs_found || 0)), [series]);
  const emailTotal = emailValues.reduce((a, b) => a + b, 0);
  const jobsTotal = jobValues.reduce((a, b) => a + b, 0);
  const max = Math.max(1, ...emailValues, ...jobValues, 0);
  const step = series.length > 1 ? (width - padX * 2) / (series.length - 1) : 0;

  const points = series.map((p, i) => {
    const emails = Number(p.emails_sent || 0);
    const jobs = Number(p.jobs_found || 0);
    const x = series.length === 1 ? width / 2 : padX + i * step;
    const emailY = height - padY - (emails / max) * (height - padY * 2);
    const jobsY = height - padY - (jobs / max) * (height - padY * 2);
    return {
      x,
      emailY,
      jobsY,
      emails,
      jobs,
      label: p.label || p.date,
      date: p.date,
    };
  });

  const emailLine = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.emailY}`).join(" ");
  const jobsLine = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.jobsY}`).join(" ");
  const hovered = hoverIndex != null ? points[hoverIndex] : null;

  return (
    <article className="surface rounded-2xl p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg text-[#0b3b3a]">Outreach activity</h3>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            <span style={{ color: EMAIL_COLOR }}>Emails sent {emailTotal}</span>
            <span className="mx-2 text-[#9bb5b2]">·</span>
            <span style={{ color: JOBS_COLOR }}>Jobs found {jobsTotal}</span>
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

      <div className="mt-3 flex flex-wrap gap-4 text-sm">
        <span className="inline-flex items-center gap-2 text-[#0b3b3a]">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: EMAIL_COLOR }} />
          Emails sent
        </span>
        <span className="inline-flex items-center gap-2 text-[#0b3b3a]">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: JOBS_COLOR }} />
          Jobs found
        </span>
      </div>

      <div className="relative mt-4 w-full overflow-hidden">
        {series.length === 0 ? (
          <p className="py-16 text-center text-sm text-[var(--text-muted)]">No data for this range yet.</p>
        ) : (
          <svg
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Emails sent and jobs found"
            className="h-auto w-full"
            onMouseLeave={() => setHoverIndex(null)}
          >
            {[0, 0.25, 0.5, 0.75, 1].map((t) => {
              const y = height - padY - t * (height - padY * 2);
              return (
                <g key={t}>
                  <line x1={padX} x2={width - padX} y1={y} y2={y} stroke="#d7e8e5" strokeWidth="1" />
                  <text x={10} y={y + 4} fontSize="11" fill="#456664" fontFamily="Poppins, sans-serif">
                    {Math.round(max * t)}
                  </text>
                </g>
              );
            })}

            {emailLine && (
              <path d={emailLine} fill="none" stroke={EMAIL_COLOR} strokeWidth="2.75" strokeLinejoin="round" />
            )}
            {jobsLine && (
              <path d={jobsLine} fill="none" stroke={JOBS_COLOR} strokeWidth="2.75" strokeLinejoin="round" />
            )}

            {points.map((p, i) => (
              <g key={`${p.date}-${i}`}>
                <rect
                  x={p.x - Math.max(14, step / 2)}
                  y={padY - 10}
                  width={Math.max(28, step)}
                  height={height - padY * 2 + 20}
                  fill="transparent"
                  onMouseEnter={() => setHoverIndex(i)}
                />
                <circle
                  cx={p.x}
                  cy={p.emailY}
                  r={hoverIndex === i ? 6 : p.emails > 0 ? 4.5 : 2.5}
                  fill={EMAIL_COLOR}
                  stroke="#fff"
                  strokeWidth={hoverIndex === i ? 2 : 0}
                />
                <circle
                  cx={p.x}
                  cy={p.jobsY}
                  r={hoverIndex === i ? 6 : p.jobs > 0 ? 4.5 : 2.5}
                  fill={JOBS_COLOR}
                  stroke="#fff"
                  strokeWidth={hoverIndex === i ? 2 : 0}
                />
                {(i === 0 || i === points.length - 1 || i % Math.ceil(points.length / 7) === 0) && (
                  <text
                    x={p.x}
                    y={height - 8}
                    textAnchor="middle"
                    fontSize="11"
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
                  stroke="#0b3b3a"
                  strokeDasharray="4 4"
                  opacity="0.35"
                />
                {(() => {
                  const boxW = 176;
                  const boxH = 64;
                  const boxX = Math.min(Math.max(hovered.x - boxW / 2, 8), width - boxW - 8);
                  const tipY = Math.min(hovered.emailY, hovered.jobsY);
                  const boxY = Math.max(8, tipY - boxH - 12);
                  return (
                    <>
                      <rect x={boxX} y={boxY} width={boxW} height={boxH} rx={12} fill="#0b3b3a" opacity="0.96" />
                      <text
                        x={boxX + 14}
                        y={boxY + 20}
                        fontSize="11"
                        fill="#cde8e4"
                        fontFamily="Poppins, sans-serif"
                      >
                        {hovered.label}
                      </text>
                      <text
                        x={boxX + 14}
                        y={boxY + 40}
                        fontSize="12"
                        fontWeight="600"
                        fill={EMAIL_LABEL}
                        fontFamily="Poppins, sans-serif"
                      >
                        {hovered.emails} emails sent
                      </text>
                      <text
                        x={boxX + 14}
                        y={boxY + 56}
                        fontSize="12"
                        fontWeight="600"
                        fill={JOBS_LABEL}
                        fontFamily="Poppins, sans-serif"
                      >
                        {hovered.jobs} jobs found
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
