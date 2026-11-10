"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Draft = {
  id: string;
  subject: string;
  body: string;
  approval_status: string;
  to_email?: string | null;
  to_name?: string | null;
  email_status?: string | null;
  job_title?: string | null;
  company_name?: string | null;
  source_url?: string | null;
  resume_name?: string | null;
  created_at?: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export default function ReadyToSendPage() {
  const [items, setItems] = useState<Draft[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await fetch(`${API_URL}/api/v1/outreach/drafts?ready=true&limit=100`, { credentials: "include" });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    setItems(data.items || []);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function sendOne(id: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/outreach/drafts/${id}/send`, { credentials: "include",  method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      setMessage("Email sent");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-[var(--accent)]">Outreach queue</p>
          <h2 className="mt-1 text-3xl">Ready to send</h2>
          <p className="mt-2 max-w-2xl text-[var(--text-muted)]">
            Approved emails waiting to go out (auto-send uses working hours and your daily limit).
            Job vacancies need a CV attached from Drive; cold website offers send without a CV.
          </p>
        </div>
        <Link href="/" className="btn btn-secondary">
          Back to dashboard
        </Link>
      </header>

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

      <p className="text-sm text-[var(--text-muted)]">{items.length} email{items.length === 1 ? "" : "s"} ready</p>

      <div className="space-y-3">
        {items.map((draft) => (
          <article key={draft.id} className="surface rounded-2xl p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="mb-2 flex flex-wrap gap-2">
                  <span className="chip chip-teal">{draft.approval_status}</span>
                  {draft.email_status && <span className="chip">{draft.email_status} email</span>}
                  {draft.resume_name && <span className="chip chip-info">CV: {draft.resume_name}</span>}
                </div>
                <h3 className="text-xl text-[var(--heading)]">{draft.subject}</h3>
                <p className="mt-1 text-[var(--text-muted)]">
                  {draft.job_title || "Untitled role"}
                  {draft.company_name ? ` · ${draft.company_name}` : ""}
                </p>
                <p className="mt-1 text-sm text-[var(--text-muted)]">
                  To: {[draft.to_name, draft.to_email].filter(Boolean).join(" · ") || "—"}
                </p>
              </div>
              <p className="text-sm text-[var(--text-muted)]">
                {draft.created_at ? new Date(draft.created_at).toLocaleString() : ""}
              </p>
            </div>
            <pre className="mt-4 max-h-40 overflow-auto whitespace-pre-wrap rounded-xl bg-[var(--bg-soft)] p-3 text-sm text-[var(--heading)]">
              {draft.body}
            </pre>
            <div className="mt-4 flex flex-wrap gap-2">
              {draft.source_url && (
                <a className="btn btn-secondary" href={draft.source_url} target="_blank" rel="noreferrer">
                  Open listing
                </a>
              )}
              <button className="btn btn-primary" disabled={busy} onClick={() => sendOne(draft.id)}>
                Send now
              </button>
            </div>
          </article>
        ))}
        {items.length === 0 && !error && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">
            No emails are ready to send right now.
          </div>
        )}
      </div>
    </div>
  );
}
