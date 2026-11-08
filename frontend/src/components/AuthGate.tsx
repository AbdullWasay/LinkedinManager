"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, SessionUser } from "@/lib/api";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        if (me.auth_required && !me.authenticated && pathname !== "/login") {
          router.replace("/login");
          return;
        }
        if (me.authenticated && pathname === "/login") {
          router.replace("/");
          return;
        }
        setReady(true);
      })
      .catch(() => {
        if (cancelled) return;
        if (pathname !== "/login") router.replace("/login");
        else setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] text-[var(--text-muted)]">
        Checking login…
      </div>
    );
  }

  if (user?.auth_required && !user.authenticated) {
    return null;
  }

  return <>{children}</>;
}
