"use client";

import { FormEvent, useEffect, useState } from "react";
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
  const [businessName, setBusinessName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [market, setMarket] = useState("UK");
  const [city, setCity] = useState("");
  const [businessType, setBusinessType] = useState("local business");
  const [sourceUrl, setSourceUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [confirmNoWebsite, setConfirmNoWebsite] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await fetch(`${API_URL}/api/v1/cold-leads`, { credentials: "include" });
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
      const res = await fetch(`${API_URL}/api/v1/cold-leads`, { credentials: "include", 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: businessName,
          owner_name: ownerName,
          owner_email: ownerEmail,
          market,
          city: city || null,
          business_type: businessType,
          source_url: sourceUrl || null,
          notes: notes || null,
          confirm_no_website: confirmNoWebsite,
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
      setBusinessName("");
      setOwnerName("");
      setOwnerEmail("");
      setCity("");
      setBusinessType("local business");
      setSourceUrl("");
      setNotes("");
      setConfirmNoWebsite(false);
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
        <p className="text-sm font-semibold text-[var(--accent)]">Agency outreach</p>
        <h2 className="mt-1 text-3xl">Cold website offers</h2>
        <p className="mt-2 text-[var(--text-muted)]">
          Add UK/US business owners who have no website. We draft a short offer email (portfolio
          link, no CV) and include it in the daily 30-send queue.
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
            <label className="label" htmlFor="cw-business">
              Business name
            </label>
            <input
              id="cw-business"
              className="input"
              required
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              placeholder="Rosewood Dental"
            />
          </div>
          <div>
            <label className="label" htmlFor="cw-type">
              Business type
            </label>
            <input
              id="cw-type"
              className="input"
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
              placeholder="salon, cafe, plumber…"
            />
          </div>
          <div>
            <label className="label" htmlFor="cw-owner">
              Owner name
            </label>
            <input
              id="cw-owner"
              className="input"
              required
              value={ownerName}
              onChange={(e) => setOwnerName(e.target.value)}
              placeholder="Sarah Khan"
            />
          </div>
          <div>
            <label className="label" htmlFor="cw-email">
              Owner email
            </label>
            <input
              id="cw-email"
              className="input"
              type="email"
              required
              value={ownerEmail}
              onChange={(e) => setOwnerEmail(e.target.value)}
              placeholder="sarah@…"
            />
          </div>
          <div>
            <label className="label" htmlFor="cw-market">
              Market
            </label>
            <select
              id="cw-market"
              className="input"
              value={market}
              onChange={(e) => setMarket(e.target.value)}
            >
              <option value="UK">UK</option>
              <option value="US">US</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="cw-city">
              City
            </label>
            <input
              id="cw-city"
              className="input"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="Manchester / Austin"
            />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="cw-url">
            Source (Google Maps / directory URL, optional)
          </label>
          <input
            id="cw-url"
            className="input"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="https://maps.google.com/…"
          />
        </div>
        <div>
          <label className="label" htmlFor="cw-notes">
            Notes
          </label>
          <textarea
            id="cw-notes"
            className="input min-h-[80px]"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="No website found; email from directory listing…"
          />
        </div>
        <label className="flex items-start gap-3 text-sm text-[var(--text-muted)]">
          <input
            type="checkbox"
            className="mt-1"
            checked={confirmNoWebsite}
            onChange={(e) => setConfirmNoWebsite(e.target.checked)}
          />
          <span>
            I confirmed this is a real UK/US business owner contact and they do not have a proper
            website.
          </span>
        </label>
        <button className="btn btn-primary" type="submit" disabled={busy || !confirmNoWebsite}>
          {busy ? "Saving…" : "Save & queue email"}
        </button>
      </form>

      <section className="space-y-3">
        <h3 className="text-lg text-[#0b3b3a]">Saved cold leads ({items.length})</h3>
        {items.map((lead) => (
          <article key={lead.id} className="surface rounded-2xl p-4">
            <div className="mb-2 flex flex-wrap gap-2">
              <span className="chip chip-teal">Cold website</span>
              {lead.market && <span className="chip">{lead.market}</span>}
              {lead.business_type && <span className="chip">{lead.business_type}</span>}
            </div>
            <h4 className="text-lg text-[#0b3b3a]">{lead.company_name || lead.title}</h4>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {[lead.location, lead.apply_email].filter(Boolean).join(" · ") || "—"}
            </p>
          </article>
        ))}
        {items.length === 0 && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">
            No cold website leads yet. Add verified UK/US owners above.
          </div>
        )}
      </section>
    </div>
  );
}
