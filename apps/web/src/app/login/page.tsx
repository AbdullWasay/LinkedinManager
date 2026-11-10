"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { api } from "@/lib/api";

// Google OAuth must hit the backend host directly (redirect URI is registered there).
const GOOGLE_API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [methods, setMethods] = useState<{ password?: boolean; google?: boolean }>({});

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const handoff = params.get("handoff");
    if (handoff) {
      setBusy(true);
      api
        .consumeHandoff(handoff)
        .then(() => router.replace("/"))
        .catch((err: Error) => {
          setError(err.message || "Google sign-in failed");
          setBusy(false);
        });
      return;
    }
    api
      .me()
      .then((me) => {
        setMethods(me.login_methods || {});
        if (me.authenticated) router.replace("/");
      })
      .catch(() => undefined);
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle compact />
      </div>
      <div className="surface w-full max-w-md rounded-3xl p-8">
        <p className="text-sm font-semibold text-[var(--accent)]">Private access</p>
        <h1 className="mt-2 text-3xl text-[var(--heading)]">Sign in</h1>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          Only your allowlisted account can open this dashboard.
        </p>

        {error && (
          <div className="mt-4 rounded-xl border border-[color:#fecaca] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--danger)]">
            {error}
          </div>
        )}

        {methods.password !== false && (
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="label" htmlFor="password">
                App password
              </label>
              <input
                id="password"
                type="password"
                className="input"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
              />
            </div>
            <button className="btn btn-primary w-full" type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in with password"}
            </button>
          </form>
        )}

        {methods.google && (
          <div className="mt-4">
            <a className="btn btn-secondary w-full" href={`${GOOGLE_API_URL}/api/v1/auth/google/login`}>
              Sign in with Google
            </a>
            <p className="mt-2 text-xs text-[var(--text-muted)]">
              Google sign-in only works for emails listed in ALLOWED_LOGIN_EMAILS.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
