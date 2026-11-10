"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { SoftLoader } from "@/components/SoftLoader";
import { displayEmail } from "@/lib/display";

type Job = {
  id: string;
  title: string;
  company_name?: string | null;
  source: string;
  source_url?: string | null;
  location?: string | null;
  employment_type?: string | null;
  is_remote: boolean;
  salary_range?: string | null;
  status: string;
  match_score?: number | null;
  application_mode?: string;
  apply_url?: string | null;
  apply_email?: string | null;
  manual_apply_required?: boolean;
  manual_apply_status?: string;
  posted_at?: string | null;
  discovered_at?: string | null;
  match_details?: {
    relevant_strengths?: string[];
    potential_concerns?: string[];
    recommended_action?: string;
    freshness?: string;
    application?: {
      detection_reason?: string;
      email_status?: string;
      apply_method?: string;
      api_endpoint?: string;
    };
  };
};

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

type ScoreFilter = "any" | "70" | "55";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [minScore, setMinScore] = useState<ScoreFilter>("any");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load(opts?: { minScore?: ScoreFilter }) {
    const nextScore = opts?.minScore ?? minScore;
    const params = new URLSearchParams({
      remote_only: "true",
      limit: "100",
      application_mode: "email",
    });
    if (nextScore !== "any") params.set("min_score", nextScore);

    const res = await fetch(`${API_URL}/api/v1/jobs?${params}`, { credentials: "include" });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    // Email outreach only — never show API/POST-apply or already-sent items.
    const hiddenStatus = new Set(["applied", "sent", "rejected", "closed"]);
    const items: Job[] = (data.items || []).filter((j: Job) => {
      if (j.source === "cold_website") return false;
      if (hiddenStatus.has(String(j.status || "").toLowerCase())) return false;
      if (j.application_mode === "api_apply") return false;
      if (j.application_mode === "email" && j.apply_email) {
        const status = j.match_details?.application?.email_status;
        return status !== "guessed";
      }
      return false;
    });
    setJobs(items);
    setTotal(items.length);
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const scoreParam = params.get("min_score");
    const nextScore: ScoreFilter = scoreParam === "70" || scoreParam === "55" ? scoreParam : "any";
    setMinScore(nextScore);
    setLoading(true);
    load({ minScore: nextScore })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function syncUrl(next: { minScore: ScoreFilter }) {
    const url = new URL(window.location.href);
    url.searchParams.delete("mode");
    url.searchParams.delete("view");
    if (next.minScore === "any") url.searchParams.delete("min_score");
    else url.searchParams.set("min_score", next.minScore);
    window.history.replaceState({}, "", url.toString());
  }

  async function applyFilters(next: { minScore?: ScoreFilter }) {
    const payload = {
      minScore: next.minScore ?? minScore,
    };
    setMinScore(payload.minScore);
    syncUrl(payload);
    setError(null);
    try {
      await load(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    }
  }

  async function discover() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/jobs/discover?min_score=55&sync_sheets=false`, { credentials: "include", 
        method: "POST",
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      await fetch(`${API_URL}/api/v1/jobs/reclassify-modes`, { credentials: "include",  method: "POST" }).catch(() => undefined);
      const purged = await fetch(`${API_URL}/api/v1/jobs/purge-inauthentic`, { credentials: "include",  method: "POST" })
        .then((r) => r.json())
        .catch(() => null);
      const removed = purged?.removed ?? 0;
      setMessage(
        `Discovery done: fetched ${data.fetched}, saved ${data.saved}, updated ${data.updated}` +
          (removed ? `, removed ${removed} inauthentic` : "") +
          "."
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed");
    } finally {
      setBusy(false);
    }
  }

  async function setManualStatus(jobId: string, manual_apply_status: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/jobs/${jobId}/manual-apply`, { credentials: "include", 
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manual_apply_status }),
      });
      if (!res.ok) throw new Error(await res.text());
      await load();
      setMessage(`Marked job as ${manual_apply_status}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return jobs;
    return jobs.filter((job) =>
      [job.title, job.company_name, job.location, job.apply_email, job.source]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q))
    );
  }, [jobs, query]);

  function modeChip(job: Job) {
    if (job.source === "cold_website") return <span className="chip chip-info">Cold website offer</span>;
    if (job.application_mode === "email" || !job.manual_apply_required)
      return <span className="chip chip-teal">Email outreach</span>;
    return <span className="chip chip-warn">Manual form apply</span>;
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-[var(--accent)]">Outreach</p>
          <h2 className="mt-1 text-3xl">Remote job matches</h2>
          <p className="mt-2 max-w-2xl text-[var(--text-muted)]">
            Email-apply roles only. API/POST apply listings and form-board scrapes are excluded.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/ready-to-send" className="btn btn-secondary">
            Ready to send
          </Link>
          <button className="btn btn-primary" disabled={busy} onClick={discover}>
            {busy ? (
              <span className="inline-flex items-center gap-2">
                <span className="boot-spinner h-4 w-4" aria-hidden />
                Working
              </span>
            ) : (
              "Discover jobs now"
            )}
          </button>
        </div>
      </header>

      <section className="surface rounded-2xl p-4 space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="label" htmlFor="score-filter">
              Min match score
            </label>
            <select
              id="score-filter"
              className="select"
              value={minScore}
              onChange={(e) => applyFilters({ minScore: e.target.value as ScoreFilter })}
            >
              <option value="any">Any score</option>
              <option value="55">55%+</option>
              <option value="70">70%+</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="job-search">
              Search
            </label>
            <input
              id="job-search"
              className="input"
              placeholder="Title, company, email…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>
      </section>

      {message && (
        <div className="surface rounded-2xl border-[color:#99f6e4] px-4 py-3 text-sm text-[#115e59]">
          {message}
        </div>
      )}
      {error && (
        <div className="surface rounded-2xl border-[color:#fecaca] px-4 py-3 text-sm text-[var(--danger)]">
          {error}
        </div>
      )}

      <p className="text-sm text-[var(--text-muted)]">
        Showing {filtered.length} of {total} jobs
      </p>

      {loading && <SoftLoader compact label="Loading jobs" />}

      <div className="space-y-3">
        {!loading &&
          filtered.map((job) => {
          const sourceLink = job.source_url || job.apply_url;
          const isEmail = job.application_mode === "email" || !job.manual_apply_required;
          const email = displayEmail(job.apply_email);

          return (
            <article key={job.id} className="surface overflow-hidden rounded-2xl p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap gap-2">
                    {modeChip(job)}
                    {job.match_details?.freshness === "24h" && (
                      <span className="chip chip-teal">Posted last 24h</span>
                    )}
                    {job.match_details?.freshness === "7d" && <span className="chip">Within 7 days</span>}
                    {isEmail && job.match_details?.application?.email_status === "guessed" && (
                      <span className="chip chip-warn">Guessed email — not auto-sent</span>
                    )}
                  </div>
                  <h3 className="break-words text-xl text-[var(--heading)]">{job.title}</h3>
                  <p className="mt-1 break-words text-[var(--text-muted)]">
                    {job.company_name || "Unknown company"}
                    {job.location ? ` · ${job.location}` : ""}
                  </p>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">Source channel: {job.source}</p>
                </div>
                <div className="shrink-0 rounded-2xl bg-[var(--accent-soft)] px-3 py-2 text-right">
                  <div className="text-2xl font-semibold text-[var(--accent)]">
                    {job.match_score != null ? `${Math.round(job.match_score)}%` : "—"}
                  </div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">
                    match
                  </div>
                </div>
              </div>

              <div className="meta-grid mt-4">
                {job.salary_range && (
                  <div className="meta-item">
                    <span className="meta-label">Pay</span>
                    <span className="meta-value">{job.salary_range}</span>
                  </div>
                )}
                <div className="meta-item">
                  <span className="meta-label">Work mode</span>
                  <span className="meta-value">{job.is_remote ? "Remote" : "Not remote"}</span>
                </div>
                {email && (
                  <div className="meta-item">
                    <span className="meta-label">Email</span>
                    <span className="meta-value">{email}</span>
                  </div>
                )}
                {job.discovered_at && (
                  <div className="meta-item">
                    <span className="meta-label">Found</span>
                    <span className="meta-value">{new Date(job.discovered_at).toLocaleString()}</span>
                  </div>
                )}
              </div>

              {sourceLink && (
                <p className="mt-3 break-all text-sm">
                  <span className="text-[var(--text-muted)]">Listing: </span>
                  <a
                    className="font-semibold text-[var(--accent)] underline"
                    href={sourceLink}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {sourceLink}
                  </a>
                </p>
              )}

              {job.match_details?.application?.detection_reason && (
                <p className="mt-3 break-words rounded-xl bg-[var(--bg-soft)] px-3 py-2 text-sm text-[var(--text-muted)]">
                  <span className="font-semibold text-[var(--heading)]">Why: </span>
                  {job.match_details.application.detection_reason}
                </p>
              )}

              <div className="mt-4 flex flex-wrap gap-2">
                {sourceLink && (
                  <a className="btn btn-primary" href={sourceLink} target="_blank" rel="noreferrer">
                    Open listing
                  </a>
                )}
                {!isEmail && job.manual_apply_status === "pending" && (
                  <>
                    <button
                      className="btn btn-secondary"
                      disabled={busy}
                      onClick={() => setManualStatus(job.id, "applied")}
                    >
                      I applied
                    </button>
                    <button
                      className="btn btn-secondary"
                      disabled={busy}
                      onClick={() => setManualStatus(job.id, "skipped")}
                    >
                      Skip
                    </button>
                  </>
                )}
              </div>
            </article>
          );
        })}
        {!loading && filtered.length === 0 && !error && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">No jobs match these filters.</div>
        )}
      </div>
    </div>
  );
}
