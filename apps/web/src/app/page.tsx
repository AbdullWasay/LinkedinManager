"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  AnalyticsOverview,
  ActivitySummaryItem,
  DailyPoint,
  NextSendInfo,
} from "@/lib/api";
import { AnalyticsChart } from "@/components/AnalyticsChart";
import { NextSendTimer } from "@/components/NextSendTimer";

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [series, setSeries] = useState<DailyPoint[]>([]);
  const [activity, setActivity] = useState<ActivitySummaryItem[]>([]);
  const [nextSend, setNextSend] = useState<NextSendInfo | null>(null);
  const [range, setRange] = useState("7d");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.analytics(), api.activitySummary(10), api.nextSend()])
      .then(([a, summary, next]) => {
        setAnalytics(a);
        setActivity(summary.items || []);
        setNextSend(next || a.next_send || null);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    api
      .analyticsDaily(range)
      .then((daily) => setSeries(daily.series || []))
      .catch((err: Error) => setError(err.message));
  }, [range]);

  const cards = [
    {
      label: "Emails ready to send",
      value: analytics?.emails_ready_to_send ?? "—",
      href: "/ready-to-send",
      hint: "Approved drafts waiting for the next send window",
    },
    {
      label: "Emails already sent",
      value: analytics?.emails_sent ?? "—",
      href: "/applications",
      hint: "Outbound emails delivered so far",
    },
    {
      label: "Roles applied",
      value: analytics?.applications_sent ?? "—",
      href: "/applications",
      hint: "Roles marked sent or further",
    },
    {
      label: "Email outreach pool",
      value: analytics?.email_outreach_jobs ?? "—",
      href: "/jobs",
      hint: "Jobs with email apply mode (not all are ready yet)",
    },
    {
      label: "Jobs discovered",
      value: analytics?.jobs_discovered ?? "—",
      href: "/jobs",
      hint: "All saved remote matches",
    },
    {
      label: "Avg match score",
      value: analytics ? `${analytics.avg_match_score.toFixed(1)}%` : "—",
      href: "/jobs?min_score=70",
      hint: "Across scored opportunities",
    },
  ];

  return (
    <div className="space-y-7">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-[var(--accent)]">Overview</p>
          <h2 className="mt-1 text-3xl">Dashboard</h2>
          <p className="mt-2 max-w-2xl text-[var(--text-muted)]">
            Ready drafts, send windows, and outreach performance in one place.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/ready-to-send" className="btn btn-primary">
            Ready to send
          </Link>
          <Link href="/applications" className="btn btn-secondary">
            Applied roles
          </Link>
        </div>
      </header>

      {error && (
        <div className="surface rounded-2xl border-[color:#fecaca] px-4 py-3 text-sm text-[var(--danger)]">
          API error: {error}
        </div>
      )}

      <section className="grid gap-4 xl:grid-cols-[1.55fr_0.9fr]">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {cards.map((card) => (
            <Link key={card.label} href={card.href} className="kpi-card surface rounded-2xl p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                {card.label}
              </p>
              <p className="mt-2 text-3xl font-semibold text-[#0b3b3a]">{card.value}</p>
              <p className="mt-2 text-sm text-[var(--text-muted)]">{card.hint}</p>
            </Link>
          ))}
        </div>
        <NextSendTimer initial={nextSend} />
      </section>

      <section>
        <AnalyticsChart series={series} range={range} onRangeChange={setRange} />
      </section>

      <section className="surface rounded-2xl p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-xl">Recent activity</h3>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Grouped summaries</p>
          </div>
          <Link href="/activity" className="text-sm font-semibold text-[var(--accent)]">
            Full activity →
          </Link>
        </div>
        <div className="mt-4 space-y-2.5">
          {activity.length === 0 && (
            <p className="text-sm text-[var(--text-muted)]">No grouped activity yet.</p>
          )}
          {activity.map((item) => (
            <div
              key={item.key}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-soft)] px-4 py-3"
            >
              <div>
                <p className="font-semibold text-[#0b3b3a]">{item.title}</p>
                <p className="mt-0.5 text-sm text-[var(--text-muted)]">
                  {item.created_at ? new Date(item.created_at).toLocaleString() : "—"}
                </p>
              </div>
              <span className="chip chip-teal">{item.count}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
