"use client";

import { useEffect, useState } from "react";

type NextSend = {
  status?: string;
  seconds_until_start?: number | null;
  timezone?: string | null;
  local_window?: string;
  message?: string;
  any_open_now?: boolean;
  starts_at?: string | null;
  emails_ready?: number;
  emails_in_next_batch?: number;
  daily_send_limit?: number;
  sent_today?: number;
  remaining_today?: number;
};

function formatCountdown(totalSeconds: number) {
  const s = Math.max(0, totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export function NextSendTimer({ initial }: { initial: NextSend | null }) {
  const [info, setInfo] = useState<NextSend | null>(initial);
  const [seconds, setSeconds] = useState<number>(initial?.seconds_until_start ?? 0);

  useEffect(() => {
    setInfo(initial);
    setSeconds(initial?.seconds_until_start ?? 0);
  }, [initial]);

  useEffect(() => {
    if (info?.any_open_now) return;
    const id = setInterval(() => setSeconds((v) => Math.max(0, v - 1)), 1000);
    return () => clearInterval(id);
  }, [info?.any_open_now]);

  useEffect(() => {
    const id = setInterval(() => {
      fetch(`${(process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "")}/api/v1/analytics/next-send`, { credentials: "include" })
        .then((r) => r.json())
        .then((data) => {
          setInfo(data);
          setSeconds(data.seconds_until_start ?? 0);
        })
        .catch(() => undefined);
    }, 60000);
    return () => clearInterval(id);
  }, []);

  const batchCount = info?.emails_in_next_batch ?? 0;
  const ready = info?.emails_ready ?? 0;
  const limit = info?.daily_send_limit;
  const sentToday = info?.sent_today ?? 0;

  return (
    <article className="surface rounded-2xl p-5">
      <p className="text-sm font-semibold text-[var(--accent)]">Next email batch</p>
      <p className="mt-2 text-3xl font-semibold text-[#0b3b3a]">
        {info?.any_open_now ? "Sending window open" : formatCountdown(seconds)}
      </p>
      <p className="mt-3 text-2xl font-semibold text-[#0b3b3a]">
        {batchCount} email{batchCount === 1 ? "" : "s"} in next batch
      </p>
      <p className="mt-2 text-sm text-[var(--text-muted)]">
        {info?.message || "Calculating working-hours window…"}
      </p>
      <p className="mt-1 text-sm text-[var(--text-muted)]">
        {ready} ready · {sentToday}
        {limit != null ? `/${limit}` : ""} sent today
        {limit != null ? ` · room for ${info?.remaining_today ?? 0} more` : ""}
      </p>
    </article>
  );
}
