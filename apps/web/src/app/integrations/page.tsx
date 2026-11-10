"use client";

import { useEffect, useState } from "react";
import { api, AuthStatus } from "@/lib/api";

export default function IntegrationsPage() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setAuth(await api.authStatus());
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      await fn();
      setMessage(`${label} succeeded`);
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
        <p className="text-sm font-semibold text-[var(--accent)]">Integrations</p>
        <h2 className="mt-1 text-3xl">Google</h2>
        <p className="mt-2 text-[var(--text-muted)]">
          Connect Gmail + Drive so outreach can send with your CV attached. Google Sheets sync is
          turned off.
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

      <section className="surface space-y-4 rounded-2xl p-5">
        <h3 className="text-xl text-[var(--heading)]">Connection</h3>
        <ul className="space-y-2 text-sm text-[var(--text-muted)]">
          <li>Google OAuth configured: {auth?.google_configured ? "yes" : "no"}</li>
          <li>Connected: {auth?.google_connected ? "yes" : "no"}</li>
          <li>Account: {auth?.email || "—"}</li>
          <li>Drive folder: {auth?.drive_folder_id || "not created yet"}</li>
          <li>Sheets sync: disabled</li>
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
          <button
            className="btn btn-secondary"
            disabled={!!busy}
            onClick={() => run("Gmail reconcile", api.reconcileEmails)}
          >
            {busy === "Gmail reconcile" ? "Working…" : "Reconcile Gmail"}
          </button>
        </div>
      </section>
    </div>
  );
}
