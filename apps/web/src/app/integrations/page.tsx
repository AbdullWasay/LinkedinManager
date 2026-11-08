"use client";

import { useEffect, useState } from "react";
import { api, AuthStatus, SyncStatus } from "@/lib/api";

export default function IntegrationsPage() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [a, s] = await Promise.all([api.authStatus(), api.syncStatus()]);
    setAuth(a);
    setSync(s);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      const result = await fn();
      setMessage(`${label} succeeded: ${JSON.stringify(result)}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">Phase 2</p>
        <h2 className="mt-1 font-[family-name:var(--font-display)] text-3xl">Google Integrations</h2>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          OAuth connects Sheets, Gmail, and Drive. Tokens are encrypted at rest. Spreadsheet{" "}
          <strong>AI Job Hunter - Abdul Wasay</strong> is created automatically on first connect.
        </p>
      </header>

      {error && <div className="surface rounded-xl px-4 py-3 text-sm text-[#ffd5cf]">{error}</div>}
      {message && <div className="surface rounded-xl px-4 py-3 text-sm text-[#b8f0cf] break-all">{message}</div>}

      <section className="surface space-y-4 rounded-xl p-5">
        <h3 className="font-[family-name:var(--font-display)] text-xl">Connection</h3>
        <ul className="space-y-2 text-sm">
          <li>Google OAuth configured: {auth?.google_configured ? "yes" : "no — add client ID/secret to .env"}</li>
          <li>Connected: {auth?.google_connected ? "yes" : "no"}</li>
          <li>Account email (app user): {auth?.email || "—"}</li>
          <li>
            Spreadsheet:{" "}
            {auth?.spreadsheet_url ? (
              <a className="underline" href={auth.spreadsheet_url} target="_blank" rel="noreferrer">
                {auth.spreadsheet_id}
              </a>
            ) : (
              "not created"
            )}
          </li>
          <li>Drive folder ID: {auth?.drive_folder_id || "not created"}</li>
        </ul>
        <div className="flex flex-wrap gap-2">
          <a className="btn btn-primary" href={api.googleLoginUrl}>
            Connect Google
          </a>
          <button
            className="btn btn-secondary"
            disabled={!!busy || !auth?.google_connected}
            onClick={() => run("Disconnect", api.disconnectGoogle)}
          >
            Disconnect
          </button>
        </div>
      </section>

      <section className="surface space-y-4 rounded-xl p-5">
        <h3 className="font-[family-name:var(--font-display)] text-xl">Sheets sync</h3>
        <p className="text-sm text-[var(--text-muted)]">
          UUID-keyed two-way sync. Push writes DB → Sheets. Pull imports Blocklist, Settings, and Application Tracker edits.
        </p>
        <div className="flex flex-wrap gap-2">
          <button className="btn btn-secondary" disabled={!!busy} onClick={() => run("Push", api.pushSheets)}>
            {busy === "Push" ? "Pushing…" : "Push to Sheets"}
          </button>
          <button className="btn btn-secondary" disabled={!!busy} onClick={() => run("Pull", api.pullSheets)}>
            {busy === "Pull" ? "Pulling…" : "Pull from Sheets"}
          </button>
          <button className="btn btn-primary" disabled={!!busy} onClick={() => run("Full sync", api.fullSync)}>
            {busy === "Full sync" ? "Syncing…" : "Full sync"}
          </button>
          <button
            className="btn btn-secondary"
            disabled={!!busy}
            onClick={() => run("Gmail reconcile", api.reconcileEmails)}
          >
            Reconcile Gmail
          </button>
        </div>
        <div className="mt-2 space-y-2">
          {(sync?.resources || []).length === 0 && (
            <p className="text-sm text-[var(--text-muted)]">No sync history yet.</p>
          )}
          {(sync?.resources || []).map((r) => (
            <div key={r.resource} className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm">
              <div className="font-medium">{r.resource}</div>
              <div className="text-[var(--text-muted)]">
                pushed {r.last_pushed_at ? new Date(r.last_pushed_at).toLocaleString() : "—"} · pulled{" "}
                {r.last_pulled_at ? new Date(r.last_pulled_at).toLocaleString() : "—"}
              </div>
              {r.last_error && <div className="text-[#ffd5cf]">{r.last_error}</div>}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
