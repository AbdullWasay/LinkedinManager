"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Lead = {
  id: string;
  title: string;
  company_name?: string | null;
  source_url?: string | null;
  apply_email?: string | null;
  posted_at?: string | null;
  status?: string;
  source?: string;
  contact_role?: string | null;
  source_channel?: string | null;
  match_score?: number | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export default function LinkedInLeadsPage() {
  const [items, setItems] = useState<Lead[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await fetch(`${API_URL}/api/v1/linkedin-leads`, { credentials: "include" });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const hidden = new Set(["applied", "sent", "rejected", "closed"]);
    setItems(
      (data.items || []).filter((item: Lead) => !hidden.has(String(item.status || "").toLowerCase()))
    );
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function runDiscovery() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/linkedin-leads/discover`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        let detail = await res.text();
        try {
          const body = JSON.parse(detail);
          detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        } catch {
          /* keep text */
        }
        throw new Error(detail);
      }
      const data = await res.json();
      setMessage(data.message || "Research finished");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">Founder / hiring leads</p>
        <h2 className="mt-1 text-3xl">Auto research</h2>
        <p className="mt-2 text-[var(--text-muted)]">
          The system finds startup founders, CEOs, and hiring managers who are actively hiring and
          already list a public email — then drafts outreach. No manual form.
        </p>
      </header>

      {error && (
        <div className="surface rounded-2xl border-[color:#fecaca] px-4 py-3 text-sm text-[var(--danger)]">
          {error}
        </div>
      )}
      {message && (
        <div className="surface rounded-2xl border-[color:#99f6e4] px-4 py-3 text-sm text-[#115e59]">
          {message}{" "}
          <Link href="/ready-to-send" className="font-semibold underline">
            Open ready to send
          </Link>
        </div>
      )}

      <div className="surface flex flex-wrap items-center justify-between gap-3 rounded-2xl p-5">
        <div>
          <h3 className="text-lg text-[#0b3b3a]">Daily auto research</h3>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Pulls HN Who is hiring, YC startups, and founder-flavored board posts with real emails.
            Runs on the GitHub Actions schedule — use the button to research now.
          </p>
        </div>
        <button className="btn btn-primary" type="button" disabled={busy} onClick={runDiscovery}>
          {busy ? "Researching…" : "Find hiring leads now"}
        </button>
      </div>

      <section className="space-y-3">
        <h3 className="text-xl text-[#0b3b3a]">Discovered leads ({items.length})</h3>
        {items.length === 0 && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">
            No open founder/hiring leads yet. Run research or wait for the daily job.
          </div>
        )}
        {items.map((item) => (
          <article key={item.id} className="surface rounded-2xl p-4">
            <div className="flex flex-wrap gap-2">
              <span className="chip chip-teal">founder hiring</span>
              {item.source_channel && <span className="chip">{item.source_channel}</span>}
              {item.status && <span className="chip">{item.status}</span>}
              {typeof item.match_score === "number" && (
                <span className="chip">{Math.round(item.match_score)}% match</span>
              )}
            </div>
            <h4 className="mt-2 text-lg text-[#0b3b3a]">{item.title}</h4>
            <p className="text-sm text-[var(--text-muted)]">
              {[item.company_name, item.contact_role, item.apply_email].filter(Boolean).join(" · ")}
            </p>
            {item.source_url && (
              <a
                className="mt-2 inline-block text-sm font-semibold text-[var(--accent)] underline"
                href={item.source_url}
                target="_blank"
                rel="noreferrer"
              >
                Open source
              </a>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
