"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, Profile } from "@/lib/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [skills, setSkills] = useState("");
  const [projects, setProjects] = useState("");
  const [targets, setTargets] = useState("");
  const [markets, setMarkets] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getProfile()
      .then((p) => {
        setProfile(p);
        setSkills((p.professional_background.skills || []).join(", "));
        setProjects(
          (p.projects || []).map((x) => `${x.name}${x.description ? ` — ${x.description}` : ""}`).join("\n")
        );
        setTargets((p.target_positions || []).join("\n"));
        setMarkets((p.target_markets || []).join(", "));
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!profile) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await api.updateProfile({
        full_name: profile.full_name,
        linkedin_url: profile.linkedin_url,
        portfolio_url: profile.portfolio_url,
        education: profile.education,
        professional_background: {
          ...profile.professional_background,
          skills: skills
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        },
        projects: projects
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean)
          .map((line) => {
            const [name, ...rest] = line.split("—");
            return { name: name.trim(), description: rest.join("—").trim() };
          }),
        target_positions: targets
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        target_markets: markets
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        employment_types: profile.employment_types,
        match_weights: profile.match_weights,
      });
      setProfile(updated);
      setMessage("Profile saved. Facts only — nothing invented.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (!profile && !error) {
    return <p className="text-[var(--text-muted)]">Loading profile…</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">Candidate</p>
        <h2 className="mt-1 text-4xl text-[#0b3b3a]">Profile</h2>
        <p className="mt-2 text-[var(--text-muted)]">
          Preloaded from your background. Edit freely — the system will not fabricate employment history.
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

      {profile && (
        <form onSubmit={onSubmit} className="surface space-y-4 rounded-2xl p-5">
          <div>
            <label className="label">Full name</label>
            <input
              className="input"
              value={profile.full_name}
              onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">LinkedIn</label>
              <input
                className="input"
                value={profile.linkedin_url}
                onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Portfolio</label>
              <input
                className="input"
                value={profile.portfolio_url}
                onChange={(e) => setProfile({ ...profile, portfolio_url: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="label">Current role / summary</label>
            <textarea
              className="textarea"
              value={String(profile.professional_background.summary || "")}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  professional_background: {
                    ...profile.professional_background,
                    summary: e.target.value,
                  },
                })
              }
            />
          </div>
          <div>
            <label className="label">Skills (comma-separated)</label>
            <textarea className="textarea" value={skills} onChange={(e) => setSkills(e.target.value)} />
          </div>
          <div>
            <label className="label">Projects (one per line: Name — description)</label>
            <textarea className="textarea" value={projects} onChange={(e) => setProjects(e.target.value)} />
          </div>
          <div>
            <label className="label">Target positions (one per line)</label>
            <textarea className="textarea" value={targets} onChange={(e) => setTargets(e.target.value)} />
          </div>
          <div>
            <label className="label">Target markets (comma-separated)</label>
            <input className="input" value={markets} onChange={(e) => setMarkets(e.target.value)} />
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-soft)] p-3 text-sm text-[var(--text-muted)]">
            Education: {String(profile.education.degree || "")}, {String(profile.education.institution || "")},{" "}
            {String(profile.education.year || "")}
          </div>
          <button className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save profile"}
          </button>
        </form>
      )}
    </div>
  );
}
