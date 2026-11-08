"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApplicationItem } from "@/lib/api";

const VIEWS = [
  { key: "applied", label: "Applied" },
  { key: "all", label: "All" },
] as const;

export default function ApplicationsPage() {
  const [items, setItems] = useState<ApplicationItem[]>([]);
  const [view, setView] = useState<string>("applied");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load(nextView = view) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.applications(nextView === "all" ? undefined : "applied", 100);
      setItems(data.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load applications");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get("stage") || "applied";
    const next = initial === "all" ? "all" : "applied";
    setView(next);
    load(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) =>
      [item.job_title, item.company_name, item.contact_email, item.contact_name, item.job_location]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q))
    );
  }, [items, query]);

  async function changeView(next: string) {
    setView(next);
    const url = new URL(window.location.href);
    url.searchParams.set("stage", next);
    window.history.replaceState({}, "", url.toString());
    await load(next);
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">Pipeline</p>
        <h2 className="mt-1 text-3xl">Applied roles</h2>
        <p className="mt-2 max-w-2xl text-[var(--text-muted)]">
          Roles where outreach was sent. Search by company or title.
        </p>
      </header>

      <div className="surface rounded-2xl p-4">
        <div className="filter-bar">
          {VIEWS.map((s) => (
            <button
              key={s.key}
              className={view === s.key ? "btn btn-primary" : "btn btn-secondary"}
              onClick={() => changeView(s.key)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="mt-4">
          <label className="label" htmlFor="app-search">
            Search
          </label>
          <input
            id="app-search"
            className="input"
            placeholder="Company, role, contact…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <div className="surface rounded-2xl border-[color:#fecaca] px-4 py-3 text-sm text-[var(--danger)]">
          {error}
        </div>
      )}

      <p className="text-sm text-[var(--text-muted)]">
        {loading ? "Loading…" : `${filtered.length} role${filtered.length === 1 ? "" : "s"}`}
      </p>

      <div className="space-y-3">
        {filtered.map((item) => (
          <article key={item.id} className="surface rounded-2xl p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="mb-2 flex flex-wrap gap-2">
                  <span className="chip chip-teal">Applied</span>
                  {item.match_score != null && (
                    <span className="chip">{Math.round(item.match_score)}% match</span>
                  )}
                </div>
                <h3 className="text-xl text-[#0b3b3a]">{item.job_title || "Untitled role"}</h3>
                <p className="mt-1 text-[var(--text-muted)]">
                  {item.company_name || "Unknown company"}
                  {item.job_location ? ` · ${item.job_location}` : ""}
                </p>
                {(item.contact_name || item.contact_email) && (
                  <p className="mt-2 text-sm text-[var(--text-muted)]">
                    Contact: {[item.contact_name, item.contact_email].filter(Boolean).join(" · ")}
                  </p>
                )}
              </div>
              <div className="text-right text-sm text-[var(--text-muted)]">
                Updated
                <br />
                {item.updated_at ? new Date(item.updated_at).toLocaleString() : "—"}
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {item.source_url && (
                <a className="btn btn-primary" href={item.source_url} target="_blank" rel="noreferrer">
                  Open listing
                </a>
              )}
            </div>
          </article>
        ))}
        {!loading && filtered.length === 0 && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">
            No applied roles yet.
          </div>
        )}
      </div>
    </div>
  );
}
