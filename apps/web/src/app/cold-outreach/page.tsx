"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Lead = {
  id: string;
  title: string;
  company_name?: string | null;
  location?: string | null;
  source_url?: string | null;
  apply_email?: string | null;
  status?: string;
  business_type?: string | null;
  market?: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export default function ColdOutreachPage() {
  const [items, setItems] = useState<Lead[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await fetch(`${API_URL}/api/v1/cold-leads`, { credentials: "include" });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    // Sent leads belong under Applied only.
    const hidden = new Set(["applied", "sent", "rejected", "closed"]);
    setItems((data.items || []).filter((item: Lead) => !hidden.has(String(item.status || "").toLowerCase())));
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function runDiscovery() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/cold-leads/discover`, {
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
      setMessage(data.message || "Discovery finished");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">Agency outreach</p>
        <h2 className="mt-1 text-3xl">Cold website offers</h2>
        <p className="mt-2 text-[var(--text-muted)]">
          The system automatically finds UK/US local businesses that list a public email and have no
          proper website, drafts an offer email, and includes them in the scheduled send queue.
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
          <h3 className="text-lg text-[#0b3b3a]">Auto research</h3>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Runs on schedule via GitHub Actions. Use the button to pull fresh leads now.
          </p>
        </div>
        <button className="btn btn-primary" type="button" disabled={busy} onClick={runDiscovery}>
          {busy ? "Finding businesses…" : "Find businesses now"}
        </button>
      </div>

      <section className="space-y-3">
        <h3 className="text-lg text-[#0b3b3a]">Auto-discovered leads ({items.length})</h3>
        {items.map((lead) => (
          <article key={lead.id} className="surface rounded-2xl p-4">
            <div className="mb-2 flex flex-wrap gap-2">
              <span className="chip chip-teal">Cold website</span>
              {lead.market && <span className="chip">{lead.market}</span>}
              {lead.business_type && <span className="chip">{lead.business_type}</span>}
              {lead.status && <span className="chip">{lead.status}</span>}
            </div>
            <h4 className="text-lg text-[#0b3b3a]">{lead.company_name || lead.title}</h4>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {[lead.location, lead.apply_email].filter(Boolean).join(" · ") || "—"}
            </p>
            {lead.source_url && (
              <a
                className="mt-2 inline-block text-sm font-medium text-[var(--accent)] underline"
                href={lead.source_url}
                target="_blank"
                rel="noreferrer"
              >
                Source
              </a>
            )}
          </article>
        ))}
        {items.length === 0 && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">
            No open cold leads right now. Already-emailed businesses move to{" "}
            <Link href="/applications" className="font-semibold underline">
              Applied
            </Link>
            . Click “Find businesses now” to research a fresh batch.
          </div>
        )}
      </section>
    </div>
  );
}
