"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

type Lead = {
  id: string;
  title: string;
  company_name?: string | null;
  source_url?: string | null;
  apply_email?: string | null;
  posted_at?: string | null;
  status?: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export default function LinkedInLeadsPage() {
  const [items, setItems] = useState<Lead[]>([]);
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [posterName, setPosterName] = useState("");
  const [posterEmail, setPosterEmail] = useState("");
  const [posterLinkedin, setPosterLinkedin] = useState("");
  const [notes, setNotes] = useState("");
  const [confirmReal, setConfirmReal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await fetch(`${API_URL}/api/v1/linkedin-leads`, { credentials: "include" });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    setItems(data.items || []);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/linkedin-leads`, { credentials: "include", 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          company_name: company,
          job_url: jobUrl,
          poster_name: posterName,
          poster_email: posterEmail,
          poster_linkedin: posterLinkedin || null,
          notes: notes || null,
          confirm_real_job: confirmReal,
          create_draft: true,
        }),
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
      setMessage(data.message || "Lead saved");
      setTitle("");
      setCompany("");
      setJobUrl("");
      setPosterName("");
      setPosterEmail("");
      setPosterLinkedin("");
      setNotes("");
      setConfirmReal(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save lead");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">LinkedIn</p>
        <h2 className="mt-1 text-3xl">Verified job poster outreach</h2>
        <p className="mt-2 text-[var(--text-muted)]">
          Only add live LinkedIn job posts with a real recruiter email. Test emails and fake job URLs
          are rejected.
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

      <form onSubmit={onSubmit} className="surface space-y-4 rounded-2xl p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="li-title">
              Role title
            </label>
            <input
              id="li-title"
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="li-company">
              Company
            </label>
            <input
              id="li-company"
              className="input"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              required
            />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="li-url">
            LinkedIn job URL
          </label>
          <input
            id="li-url"
            className="input"
            placeholder="https://www.linkedin.com/jobs/view/1234567890"
            value={jobUrl}
            onChange={(e) => setJobUrl(e.target.value)}
            required
          />
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            Must be a real /jobs/view/… posting (not a placeholder).
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="li-poster">
              Recruiter / poster name
            </label>
            <input
              id="li-poster"
              className="input"
              value={posterName}
              onChange={(e) => setPosterName(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="li-email">
              Recruiter work email
            </label>
            <input
              id="li-email"
              className="input"
              type="email"
              placeholder="name@company.com"
              value={posterEmail}
              onChange={(e) => setPosterEmail(e.target.value)}
              required
            />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="li-profile">
            Recruiter LinkedIn profile (optional)
          </label>
          <input
            id="li-profile"
            className="input"
            placeholder="https://www.linkedin.com/in/…"
            value={posterLinkedin}
            onChange={(e) => setPosterLinkedin(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="li-notes">
            Notes / hook (optional)
          </label>
          <textarea
            id="li-notes"
            className="textarea"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Saw your post hiring a NestJS engineer…"
          />
        </div>
        <label className="flex items-start gap-2 text-sm font-medium text-[#0b3b3a]">
          <input
            type="checkbox"
            className="mt-1"
            checked={confirmReal}
            onChange={(e) => setConfirmReal(e.target.checked)}
            required
          />
          <span>
            I confirm this is a live LinkedIn job and a real recruiter contact (not a test/placeholder).
          </span>
        </label>
        <button className="btn btn-primary" disabled={busy || !confirmReal}>
          {busy ? "Saving…" : "Save verified lead"}
        </button>
      </form>

      <section className="space-y-3">
        <h3 className="text-xl text-[#0b3b3a]">Saved LinkedIn leads</h3>
        {items.length === 0 && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">
            No LinkedIn leads yet. Add a real recruiter + live job URL above.
          </div>
        )}
        {items.map((item) => (
          <article key={item.id} className="surface rounded-2xl p-4">
            <div className="flex flex-wrap gap-2">
              <span className="chip chip-teal">linkedin poster</span>
              {item.status && <span className="chip">{item.status}</span>}
            </div>
            <h4 className="mt-2 text-lg text-[#0b3b3a]">{item.title}</h4>
            <p className="text-sm text-[var(--text-muted)]">
              {item.company_name || "Company"} · {item.apply_email}
            </p>
            {item.source_url && (
              <a
                className="mt-2 inline-block text-sm font-semibold text-[var(--accent)] underline"
                href={item.source_url}
                target="_blank"
                rel="noreferrer"
              >
                Open LinkedIn job
              </a>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
