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
import { SoftLoader } from "@/components/SoftLoader";

const KPI_STYLES = {
  cold: {
    accent: "#0f766e",
    soft: "rgba(167, 243, 208, 0.45)",
    border: "rgba(110, 231, 183, 0.55)",
  },
  openings: {
    accent: "#b45309",
    soft: "rgba(254, 215, 170, 0.5)",
    border: "rgba(253, 186, 116, 0.55)",
  },
  linkedin: {
    accent: "#1d4ed8",
    soft: "rgba(191, 219, 254, 0.55)",
    border: "rgba(147, 197, 253, 0.6)",
  },
  sent: {
    accent: "#6d28d9",
    soft: "rgba(221, 214, 254, 0.55)",
    border: "rgba(196, 181, 253, 0.6)",
  },
  ready: {
    accent: "#047857",
    soft: "rgba(167, 243, 208, 0.4)",
    border: "rgba(110, 231, 183, 0.5)",
  },
  applied: {
    accent: "#9f1239",
    soft: "rgba(254, 205, 211, 0.5)",
    border: "rgba(253, 164, 175, 0.55)",
  },
} as const;

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [series, setSeries] = useState<DailyPoint[]>([]);
  const [activity, setActivity] = useState<ActivitySummaryItem[]>([]);
  const [nextSend, setNextSend] = useState<NextSendInfo | null>(null);
  const [range, setRange] = useState("7d");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.analytics(), api.activitySummary(10), api.nextSend()])
      .then(([a, summary, next]) => {
        setAnalytics(a);
        setActivity(summary.items || []);
        setNextSend(next || a.next_send || null);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api
      .analyticsDaily(range)
      .then((daily) => setSeries(daily.series || []))
      .catch((err: Error) => setError(err.message));
  }, [range]);

  const cards = [
    {
      key: "cold",
      label: "Cold businesses found",
      value: analytics?.cold_businesses_found ?? "—",
      href: "/cold-outreach",
      hint: "Local businesses researched for website outreach",
      style: KPI_STYLES.cold,
    },
    {
      key: "openings",
      label: "Job openings found",
      value: analytics?.job_openings_found ?? "—",
      href: "/jobs",
      hint: "Companies with roles discovered for applications",
      style: KPI_STYLES.openings,
    },
    {
      key: "linkedin",
      label: "Founder / LinkedIn leads",
      value: analytics?.linkedin_leads_found ?? "—",
      href: "/linkedin",
      hint: "Founders & hiring leads researched for cold email",
      style: KPI_STYLES.linkedin,
    },
    {
      key: "sent",
      label: "Emails sent today",
      value: analytics?.emails_sent_today ?? "—",
      href: "/applications",
      hint: "Outbound emails delivered since midnight UTC",
      style: KPI_STYLES.sent,
    },
    {
      key: "ready",
      label: "Emails ready to send",
      value: analytics?.emails_ready_to_send ?? "—",
      href: "/ready-to-send",
      hint: "Approved drafts waiting in the send queue",
      style: KPI_STYLES.ready,
    },
    {
      key: "applied",
      label: "Total applied",
      value: analytics?.applications_sent ?? "—",
      href: "/applications",
      hint: "All roles emailed so far",
      style: KPI_STYLES.applied,
    },
  ] as const;

  return (
    <div className="space-y-7">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--accent)]">Overview</p>
          <h2 className="mt-1 text-2xl sm:text-3xl">Dashboard</h2>
          <p className="mt-2 max-w-2xl text-sm text-[var(--text-muted)] sm:text-base">
            Cold businesses, job openings, founder leads, and today’s send queue.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/ready-to-send" className="btn btn-primary flex-1 sm:flex-none">
            Ready to send
          </Link>
          <Link href="/applications" className="btn btn-secondary flex-1 sm:flex-none">
            Applied
          </Link>
        </div>
      </header>

      {error && (
        <div className="surface break-words rounded-2xl border-[color:#fecaca] px-4 py-3 text-sm text-[var(--danger)]">
          API error: {error}
        </div>
      )}

      {loading ? (
        <SoftLoader label="Loading dashboard" />
      ) : (
        <section className="grid gap-4 xl:grid-cols-[1.55fr_0.9fr]">
          <div className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2 xl:grid-cols-3">
            {cards.map((card) => (
              <Link
                key={card.key}
                href={card.href}
                className="kpi-card rounded-2xl p-4 transition hover:-translate-y-0.5"
                style={{
                  background: `linear-gradient(165deg, ${card.style.soft} 0%, rgba(255,255,255,0.92) 62%)`,
                  border: `1px solid ${card.style.border}`,
                  boxShadow: "0 10px 28px rgba(15, 118, 110, 0.05)",
                }}
              >
                <p
                  className="text-xs font-semibold uppercase tracking-wide"
                  style={{ color: card.style.accent, opacity: 0.88 }}
                >
                  {card.label}
                </p>
                <p className="mt-2 text-3xl font-semibold text-[#0b3b3a]">{card.value}</p>
                <p className="mt-2 text-sm text-[var(--text-muted)]">{card.hint}</p>
              </Link>
            ))}
          </div>
          <NextSendTimer initial={nextSend} />
        </section>
      )}

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
              <div className="min-w-0">
                <p className="break-words font-semibold text-[#0b3b3a]">{item.title}</p>
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
