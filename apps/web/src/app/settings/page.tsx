"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, AuthStatus, Settings } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api.getSettings(), api.authStatus()])
      .then(([s, a]) => {
        setSettings(s);
        setAuth(a);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.updateSettings({
        auto_send_enabled: settings.auto_send_enabled,
        discovery_interval_hours: settings.discovery_interval_hours,
        daily_send_limit: settings.daily_send_limit,
        follow_up_days: settings.follow_up_days,
      });
      setSettings(updated);
      setMessage("Settings saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function control(action: "pause" | "resume" | "stop") {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const fn =
        action === "pause" ? api.pauseAutomation : action === "resume" ? api.resumeAutomation : api.emergencyStop;
      const updated = await fn();
      setSettings(updated);
      setMessage(
        action === "pause"
          ? "Automation paused"
          : action === "resume"
            ? "Automation resumed"
            : "Emergency stop engaged"
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (!settings && !error) return <p className="text-[var(--text-muted)]">Loading settings…</p>;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">Controls</p>
        <h2 className="mt-1 text-4xl text-[#0b3b3a]">Settings</h2>
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

      {settings && (
        <>
          <section className="surface space-y-3 rounded-2xl p-5">
            <h3 className="text-2xl text-[#0b3b3a]">Google</h3>
            <p className="text-sm text-[var(--text-muted)]">
              Status: {auth?.google_connected ? "connected" : "not connected"} · Sheets sync runs in the
              background.
            </p>
            {auth?.spreadsheet_url && (
              <a className="btn btn-secondary" href={auth.spreadsheet_url} target="_blank" rel="noreferrer">
                Open Google Sheet
              </a>
            )}
            {!auth?.google_connected && (
              <a className="btn btn-primary" href={api.googleLoginUrl}>
                Connect Google
              </a>
            )}
          </section>

          <section className="surface space-y-3 rounded-2xl p-5">
            <h3 className="text-2xl text-[#0b3b3a]">Automation safety</h3>
            <p className="text-sm text-[var(--text-muted)]">
              Paused: {settings.automation_paused ? "yes" : "no"} · Emergency stop:{" "}
              {settings.emergency_stop ? "yes" : "no"} · Auto-send:{" "}
              {settings.auto_send_enabled ? "enabled" : "disabled"}
            </p>
            <div className="flex flex-wrap gap-2">
              <button className="btn btn-warn" disabled={busy} onClick={() => control("pause")}>
                Pause all
              </button>
              <button className="btn btn-secondary" disabled={busy} onClick={() => control("resume")}>
                Resume
              </button>
              <button className="btn btn-danger" disabled={busy} onClick={() => control("stop")}>
                Emergency stop
              </button>
            </div>
          </section>

          <form onSubmit={save} className="surface space-y-4 rounded-2xl p-5">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-soft)] p-4">
              <label className="flex items-center gap-3 text-[0.95rem] font-semibold text-[#0b3b3a]">
                <input
                  type="checkbox"
                  checked={settings.auto_send_enabled}
                  onChange={(e) => setSettings({ ...settings, auto_send_enabled: e.target.checked })}
                />
                Auto-send emails (no manual review)
              </label>
              <p className="mt-2 text-sm text-[var(--text-muted)]">
                Verified/listed emails send automatically during the recipient country’s working hours
                (weekdays 09:00–17:00 local). Guessed emails stay drafted only. Daily limit still applies.
              </p>
            </div>
            <div>
              <label className="label">Discovery interval (hours)</label>
              <input
                className="input"
                type="number"
                min={1}
                value={settings.discovery_interval_hours}
                onChange={(e) =>
                  setSettings({ ...settings, discovery_interval_hours: Number(e.target.value) })
                }
              />
            </div>
            <div>
              <label className="label">Daily send limit</label>
              <input
                className="input"
                type="number"
                min={0}
                value={settings.daily_send_limit}
                onChange={(e) => setSettings({ ...settings, daily_send_limit: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="label">Follow-up days (comma-separated)</label>
              <input
                className="input"
                value={settings.follow_up_days.join(", ")}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    follow_up_days: e.target.value
                      .split(",")
                      .map((x) => Number(x.trim()))
                      .filter((n) => !Number.isNaN(n)),
                  })
                }
              />
            </div>
            <button className="btn btn-primary" disabled={busy}>
              {busy ? "Saving…" : "Save settings"}
            </button>
          </form>
        </>
      )}
    </div>
  );
}
