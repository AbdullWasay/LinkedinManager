"use client";

import { useEffect, useMemo, useState } from "react";
import { ActivityLog, ActivitySummaryItem, api } from "@/lib/api";

type View = "grouped" | "raw";

export default function ActivityPage() {
  const [view, setView] = useState<View>("grouped");
  const [summary, setSummary] = useState<ActivitySummaryItem[]>([]);
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [category, setCategory] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.activitySummary(40), api.activityLogs(120)])
      .then(([s, l]) => {
        setSummary(s.items || []);
        setLogs(l);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const categories = useMemo(() => {
    const set = new Set(logs.map((l) => l.category).filter(Boolean));
    return ["all", ...Array.from(set).sort()];
  }, [logs]);

  const filteredLogs = useMemo(() => {
    if (category === "all") return logs;
    return logs.filter((l) => l.category === category);
  }, [logs, category]);

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">Audit</p>
        <h2 className="mt-1 text-4xl text-[#0b3b3a]">Activity</h2>
        <p className="mt-2 max-w-2xl text-[var(--text-muted)]">
          Grouped summaries first (e.g. “10 emails sent”). Switch to raw logs when you need detail.
        </p>
      </header>

      <div className="surface rounded-2xl p-4 space-y-4">
        <div className="filter-bar">
          <button
            className={view === "grouped" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => setView("grouped")}
          >
            Grouped summary
          </button>
          <button
            className={view === "raw" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => setView("raw")}
          >
            Raw logs
          </button>
        </div>
        {view === "raw" && (
          <div>
            <label className="label" htmlFor="cat-filter">
              Category
            </label>
            <select
              id="cat-filter"
              className="select max-w-xs"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c === "all" ? "All categories" : c}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {error && (
        <div className="surface rounded-2xl border-[color:#fecaca] px-4 py-3 text-sm text-[var(--danger)]">
          {error}
        </div>
      )}

      {view === "grouped" ? (
        <div className="space-y-3">
          {summary.length === 0 && !error && (
            <p className="text-[var(--text-muted)]">No grouped activity yet.</p>
          )}
          {summary.map((item) => (
            <article
              key={item.key}
              className="surface flex flex-wrap items-center justify-between gap-3 rounded-2xl px-5 py-4"
            >
              <div>
                <h3 className="text-xl text-[#0b3b3a]">{item.title}</h3>
                <p className="mt-1 text-sm text-[var(--text-muted)]">
                  {item.created_at ? new Date(item.created_at).toLocaleString() : "—"}
                </p>
              </div>
              <span className="chip chip-teal">{item.count}</span>
            </article>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {filteredLogs.length === 0 && !error && (
            <p className="text-[var(--text-muted)]">No logs in this category.</p>
          )}
          {filteredLogs.map((log) => (
            <article key={log.id} className="surface rounded-2xl px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-[var(--text-muted)]">
                <span>
                  {log.category} · {log.action} · {log.status}
                </span>
                <span>{new Date(log.created_at).toLocaleString()}</span>
              </div>
              <p className="mt-1 text-[#0b3b3a]">{log.message || "—"}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
