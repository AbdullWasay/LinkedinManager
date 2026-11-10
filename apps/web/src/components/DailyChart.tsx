"use client";

type Point = {
  date: string;
  jobs_found: number;
  emails_sent: number;
};

export function DailyChart({
  title,
  series,
  metric,
  color,
}: {
  title: string;
  series: Point[];
  metric: "jobs_found" | "emails_sent";
  color: string;
}) {
  const values = series.map((p) => p[metric]);
  const max = Math.max(1, ...values);
  const height = 160;
  const barWidth = Math.max(10, Math.floor(520 / Math.max(series.length, 1)) - 6);

  return (
    <article className="surface rounded-2xl p-5">
      <h3 className="text-xl text-[var(--heading)]">{title}</h3>
      <div className="mt-4 overflow-x-auto">
        <svg width={Math.max(520, series.length * (barWidth + 6))} height={height + 40} role="img">
          {series.map((point, index) => {
            const value = point[metric];
            const h = Math.round((value / max) * height);
            const x = index * (barWidth + 6);
            const y = height - h;
            return (
              <g key={point.date}>
                <rect x={x} y={y} width={barWidth} height={Math.max(h, value > 0 ? 4 : 0)} rx={5} fill={color} />
                <text
                  x={x + barWidth / 2}
                  y={height + 16}
                  textAnchor="middle"
                  fontSize="11"
                  fill="#4d6a68"
                  fontFamily="Source Sans 3, sans-serif"
                >
                  {point.date.slice(5)}
                </text>
                {value > 0 && (
                  <text
                    x={x + barWidth / 2}
                    y={Math.max(14, y - 6)}
                    textAnchor="middle"
                    fontSize="11"
                    fill="#102a2a"
                    fontWeight="600"
                    fontFamily="Source Sans 3, sans-serif"
                  >
                    {value}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </article>
  );
}
