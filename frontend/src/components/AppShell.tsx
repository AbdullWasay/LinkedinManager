"use client";

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
  Settings,
  Store,
  UserRound,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/ready-to-send", label: "Ready to send", icon: Mail },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/linkedin", label: "LinkedIn leads", icon: Megaphone },
  { href: "/cold-outreach", label: "Cold websites", icon: Store },
  { href: "/applications", label: "Applied", icon: CheckCircle2 },
  { href: "/cvs", label: "CVs", icon: FileText },
  { href: "/blocklist", label: "Blocklist", icon: Ban },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  if (pathname === "/login") {
    return <>{children}</>;
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      /* ignore */
    }
    router.replace("/login");
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="border-b border-[var(--border)] bg-white/90 px-4 py-5 backdrop-blur lg:border-b-0 lg:border-r">
        <div className="mb-7 px-2">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--accent)]">
            AI Job Hunter
          </p>
          <h1 className="mt-1 text-xl font-semibold text-[#0b3b3a]">Abdul Wasay</h1>
        </div>
        <nav className="flex flex-wrap gap-1.5 lg:flex-col">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "nav-link flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  active ? "nav-link-active" : "hover:bg-[var(--bg-soft)]"
                )}
              >
                <Icon size={16} className={active ? "text-white" : undefined} />
                {item.label}
              </Link>
            );
          })}
          <button
            type="button"
            onClick={logout}
            className="nav-link mt-2 flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-soft)]"
          >
            <LogOut size={16} />
            Log out
          </button>
        </nav>
      </aside>
      <main className="px-5 py-6 lg:px-8 lg:py-8">{children}</main>
    </div>
  );
}
