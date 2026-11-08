"use client";

import { FormEvent, useEffect, useState } from "react";

type Resume = {
  id: string;
  name: string;
  variant: string;
  role_labels: string[];
  keywords: string[];
  drive_url?: string | null;
  drive_file_id?: string | null;
  local_path?: string | null;
  has_file: boolean;
  is_master: boolean;
  updated_at?: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "";

export default function CvsPage() {
  const [items, setItems] = useState<Resume[]>([]);
  const [name, setName] = useState("");
  const [roles, setRoles] = useState("");
  const [keywords, setKeywords] = useState("");
  const [driveUrl, setDriveUrl] = useState("");
  const [isMaster, setIsMaster] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await fetch(`${API_URL}/api/v1/resumes`, { credentials: "include" });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    setItems(data.items || []);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/resumes`, { credentials: "include", 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          variant: name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "custom",
          role_labels: roles.split(",").map((x) => x.trim()).filter(Boolean),
          keywords: keywords.split(",").map((x) => x.trim()).filter(Boolean),
          drive_url: driveUrl || null,
          is_master: isMaster,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setName("");
      setRoles("");
      setKeywords("");
      setDriveUrl("");
      setIsMaster(false);
      setMessage("CV saved. Matching roles will use this file in outreach emails.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save CV");
    } finally {
      setBusy(false);
    }
  }

  async function uploadFile(resumeId: string, file: File) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`${API_URL}/api/v1/resumes/${resumeId}/upload`, { credentials: "include", 
        method: "POST",
        body,
      });
      if (!res.ok) throw new Error(await res.text());
      setMessage(`Uploaded ${file.name}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveDriveLink(resume: Resume, nextUrl: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/resumes/${resume.id}`, { credentials: "include", 
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ drive_url: nextUrl }),
      });
      if (!res.ok) throw new Error(await res.text());
      setMessage("Drive link updated");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveRoles(resume: Resume, nextRoles: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/resumes/${resume.id}`, { credentials: "include", 
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role_labels: nextRoles.split(",").map((x) => x.trim()).filter(Boolean),
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setMessage("Roles updated");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function makeDefault(resume: Resume) {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/resumes/${resume.id}`, { credentials: "include", 
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_master: true }),
      });
      if (!res.ok) throw new Error(await res.text());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(resume: Resume) {
    if (!confirm(`Delete ${resume.name}?`)) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/resumes/${resume.id}`, { credentials: "include",  method: "DELETE" });
      if (!res.ok) throw new Error(await res.text());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-sm font-semibold text-[var(--accent)]">Documents</p>
        <h2 className="mt-1 text-3xl">CVs by role</h2>
        <p className="mt-2 text-[var(--text-muted)]">
          Upload the PDF for each role. Drive links alone often fail until you reconnect Google with
          Drive read access — uploading the file is the reliable way to attach CVs.
        </p>
      </header>

      <div className="surface rounded-2xl border-[color:#fdba74] bg-[var(--warn-soft)] px-4 py-3 text-sm text-[#9a3412]">
        Important: emails will not send without an attached CV. Use <strong>Upload PDF</strong> on each
        CV card below (AI Engineer + Full Stack).
      </div>

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

      <form onSubmit={onCreate} className="surface space-y-4 rounded-2xl p-5">
        <h3 className="text-xl text-[#0b3b3a]">Add CV</h3>
        <div>
          <label className="label" htmlFor="cv-name">
            CV name
          </label>
          <input
            id="cv-name"
            className="input"
            placeholder="e.g. AI Engineer CV"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="label" htmlFor="cv-roles">
            Roles (comma-separated)
          </label>
          <input
            id="cv-roles"
            className="input"
            placeholder="AI Engineer, ML Engineer, LLM Engineer"
            value={roles}
            onChange={(e) => setRoles(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="label" htmlFor="cv-keywords">
            Extra keywords (optional)
          </label>
          <input
            id="cv-keywords"
            className="input"
            placeholder="llm, langchain, rag"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="cv-drive">
            Google Drive link
          </label>
          <input
            id="cv-drive"
            className="input"
            placeholder="https://drive.google.com/file/d/…"
            value={driveUrl}
            onChange={(e) => setDriveUrl(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2 text-sm font-medium text-[#0b3b3a]">
          <input type="checkbox" checked={isMaster} onChange={(e) => setIsMaster(e.target.checked)} />
          Use as default when no role match
        </label>
        <button className="btn btn-primary" disabled={busy || !name.trim() || !roles.trim()}>
          {busy ? "Saving…" : "Save CV"}
        </button>
        <p className="text-sm text-[var(--text-muted)]">
          After saving, you can also upload a local PDF on the card below. If Drive download fails,
          reconnect Google in Settings so Drive read access is granted.
        </p>
      </form>

      <div className="space-y-3">
        {items.map((resume) => (
          <article key={resume.id} className="surface space-y-3 rounded-2xl p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="mb-2 flex flex-wrap gap-2">
                  {resume.is_master && <span className="chip chip-teal">Default</span>}
                  <span className="chip">{resume.variant}</span>
                  {resume.has_file ? (
                    <span className="chip chip-teal">File linked</span>
                  ) : (
                    <span className="chip chip-warn">No file yet</span>
                  )}
                </div>
                <h3 className="text-xl text-[#0b3b3a]">{resume.name}</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {!resume.is_master && (
                  <button className="btn btn-secondary" disabled={busy} onClick={() => makeDefault(resume)}>
                    Make default
                  </button>
                )}
                <button className="btn btn-danger" disabled={busy} onClick={() => remove(resume)}>
                  Delete
                </button>
              </div>
            </div>

            <div>
              <label className="label">Roles</label>
              <input
                className="input"
                defaultValue={(resume.role_labels || []).join(", ")}
                onBlur={(e) => {
                  if (e.target.value !== (resume.role_labels || []).join(", ")) {
                    saveRoles(resume, e.target.value);
                  }
                }}
              />
            </div>

            <div>
              <label className="label">Google Drive link</label>
              <input
                className="input"
                defaultValue={resume.drive_url || ""}
                placeholder="https://drive.google.com/file/d/…"
                onBlur={(e) => {
                  if (e.target.value !== (resume.drive_url || "")) {
                    saveDriveLink(resume, e.target.value);
                  }
                }}
              />
            </div>

            <div>
              <label className="label">Upload PDF</label>
              <input
                className="input"
                type="file"
                accept=".pdf,.doc,.docx"
                disabled={busy}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadFile(resume.id, file);
                }}
              />
            </div>
          </article>
        ))}
        {items.length === 0 && (
          <div className="surface rounded-2xl p-5 text-[var(--text-muted)]">No CVs yet.</div>
        )}
      </div>
    </div>
  );
}
