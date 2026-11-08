"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type Entry = {
  id: string;
  entry_type: string;
  value: string;
  reason?: string | null;
  is_permanent: boolean;
  created_at?: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export default function BlocklistPage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [entryType, setEntryType] = useState("email");
  const [typeFilter, setTypeFilter] = useState("all");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await fetch(`${API_URL}/api/v1/blocklist`, { credentials: "include" });
    if (!res.ok) throw new Error(await res.text());
    setEntries(await res.json());
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  const filtered = useMemo(() => {
    return entries.filter((e) => {
      if (typeFilter !== "all" && e.entry_type !== typeFilter) return false;
      const q = query.trim().toLowerCase();
      if (!q) return true;
      return [e.value, e.reason, e.entry_type].filter(Boolean).some((v) => String(v).toLowerCase().includes(q));
    });
  }, [entries, typeFilter, query]);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/blocklist`, { credentials: "include", 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entry_type: entryType,
          value,
          reason: reason || null,
          is_permanent: true,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setValue("");
      setReason("");
      setMessage("Added to blocklist");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/blocklist/${id}`, { credentials: "include",  method: "DELETE" });
      if (!res.ok) throw new Error(await res.text());
      setMessage("Removed from blocklist");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">Compliance</p>
        <h2 className="mt-1 text-3xl">Blocklist</h2>
        <p className="mt-2 text-[var(--text-muted)]">
          Blocked contacts are skipped before every send.
        </p>
      </header>

      {error && (
        <div className="surface rounded-2xl border-[color:#fecaca] px-4 py-3 text-sm text-[var(--danger)]">
          {error}
        </div>
      )}
      {message && (
        <div className="surface rounded-2xl border-[color:#99f6e4] px-4 py-3 text-sm text-[#115e59]">
          {message}
        </div>
      )}

      <form onSubmit={onAdd} className="surface space-y-4 rounded-2xl p-5">
        <div className="grid gap-4 sm:grid-cols-[160px_1fr]">
          <div>
            <label className="label" htmlFor="entry-type">
              Type
            </label>
            <select
              id="entry-type"
              className="select"
              value={entryType}
              onChange={(e) => setEntryType(e.target.value)}
            >
              <option value="email">Email</option>
              <option value="domain">Domain</option>
              <option value="company">Company</option>
              <option value="person">Person</option>
              <option value="keyword">Keyword</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="entry-value">
              Value
            </label>
            <input
              id="entry-value"
              className="input"
              placeholder={entryType === "email" ? "name@company.com" : "value"}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
            />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="entry-reason">
            Reason (optional)
          </label>
          <input
            id="entry-reason"
            className="input"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" disabled={busy || !value.trim()}>
          {busy ? "Saving…" : "Add to blocklist"}
        </button>
      </form>

      <section className="surface space-y-4 rounded-2xl p-4">
        <div className="grid gap-4 md:grid-cols-[1fr_200px]">
          <div>
            <label className="label" htmlFor="block-search">
              Search
            </label>
            <input
              id="block-search"
              className="input"
              placeholder="Filter entries…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="type-filter">
              Filter by type
            </label>
            <select
              id="type-filter"
              className="select"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">All types</option>
              <option value="email">Email</option>
              <option value="domain">Domain</option>
              <option value="company">Company</option>
              <option value="person">Person</option>
              <option value="keyword">Keyword</option>
            </select>
          </div>
        </div>
      </section>

      <p className="text-sm text-[var(--text-muted)]">{filtered.length} entr{filtered.length === 1 ? "y" : "ies"}</p>

      <div className="space-y-2">
        {filtered.length === 0 && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">No blocklist entries yet.</div>
        )}
        {filtered.map((entry) => (
          <article
            key={entry.id}
            className="surface flex flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-3.5"
          >
            <div>
              <span className="chip chip-teal">{entry.entry_type}</span>
              <div className="mt-2 font-semibold text-[#0b3b3a]">{entry.value}</div>
              {entry.reason && <div className="mt-0.5 text-sm text-[var(--text-muted)]">{entry.reason}</div>}
            </div>
            <button className="btn btn-danger" disabled={busy} onClick={() => remove(entry.id)}>
              Remove
            </button>
          </article>
        ))}
      </div>
    </div>
  );
}
