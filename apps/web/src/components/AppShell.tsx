"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Ban,
  Briefcase,
  CheckCircle2,
  FileText,
  LayoutDashboard,
  LogOut,
  Mail,
  Megaphone,
  Menu,
  Settings,
  Store,
  UserRound,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/ready-to-send", label: "Ready to send", icon: Mail },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/linkedin", label: "Founder leads", icon: Megaphone },
  { href: "/cold-outreach", label: "Cold websites", icon: Store },
  { href: "/applications", label: "Applied", icon: CheckCircle2 },
  { href: "/cvs", label: "CVs", icon: FileText },
  { href: "/blocklist", label: "Blocklist", icon: Ban },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavLinks({
  pathname,
  onNavigate,
  onLogout,
}: {
  pathname: string;
  onNavigate?: () => void;
  onLogout: () => void;
}) {
  return (
    <nav className="flex flex-col gap-1" aria-label="Primary">
      {NAV.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "nav-link flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
              active ? "nav-link-active" : "hover:bg-[var(--bg-soft)]"
            )}
          >
            <Icon size={16} />
            {item.label}
          </Link>
        );
      })}
      <ThemeToggle />
      <button
        type="button"
        onClick={onLogout}
        className="nav-link mt-1 flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-soft)]"
      >
        <LogOut size={16} />
        Log out
      </button>
    </nav>
  );
}

function BrandBlock({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn(compact ? "" : "mb-7 px-2")}>
      <p className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-[var(--accent)]">
        AI Job Hunter
      </p>
      <h1
        className={cn(
          "font-semibold text-[var(--heading)]",
          compact ? "mt-0.5 text-base" : "mt-1 text-xl"
        )}
      >
        Abdul Wasay
      </h1>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const panelId = useId();

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [menuOpen]);

  if (pathname === "/login") {
    return <>{children}</>;
  }

  async function logout() {
    setMenuOpen(false);
    try {
      await api.logout();
    } catch {
      /* ignore */
    }
    router.replace("/login");
  }

  const activeLabel = NAV.find((item) => item.href === pathname)?.label || "Dashboard";

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
      <aside className="app-sidebar sticky top-0 hidden h-screen flex-col overflow-y-auto border-r border-[var(--border)] bg-[var(--bg-elevated)] px-4 py-5 lg:flex">
        <BrandBlock />
        <NavLinks pathname={pathname} onLogout={logout} />
      </aside>

      <div className="sticky top-0 z-40 border-b border-[var(--border)] bg-[var(--bg-elevated)] lg:hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <BrandBlock compact />
          <div className="flex items-center gap-2">
            <ThemeToggle compact />
            <button
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--bg-soft)] text-[var(--heading)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              aria-controls={panelId}
              onClick={() => setMenuOpen((v) => !v)}
            >
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
        <div className="border-t border-[var(--border)] bg-[var(--bg-soft)] px-4 py-2">
          <p className="text-xs font-semibold text-[var(--text-muted)]">{activeLabel}</p>
        </div>
      </div>

      <div
        className={cn("fixed inset-0 z-50 lg:hidden", menuOpen ? "pointer-events-auto" : "pointer-events-none")}
        aria-hidden={!menuOpen}
      >
        <button
          type="button"
          className={cn(
            "absolute inset-0 transition-opacity duration-200",
            menuOpen ? "opacity-100" : "opacity-0"
          )}
          style={{ background: "var(--overlay)" }}
          aria-label="Close menu overlay"
          onClick={() => setMenuOpen(false)}
        />
        <aside
          id={panelId}
          className={cn(
            "absolute inset-y-0 right-0 flex w-[min(86vw,320px)] flex-col bg-[var(--bg-elevated)] shadow-2xl transition-transform duration-200 ease-out",
            menuOpen ? "translate-x-0" : "translate-x-full"
          )}
        >
          <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-4">
            <BrandBlock compact />
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--border)] text-[var(--heading)]"
              aria-label="Close menu"
              onClick={() => setMenuOpen(false)}
            >
              <X size={18} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-4">
            <NavLinks pathname={pathname} onNavigate={() => setMenuOpen(false)} onLogout={logout} />
          </div>
          <div className="border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--text-muted)]">
            Private outreach workspace
          </div>
        </aside>
      </div>

      <main className="min-w-0 px-4 py-5 sm:px-5 sm:py-6 lg:px-8 lg:py-8">{children}</main>
    </div>
  );
}
