"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, SessionUser } from "@/lib/api";

function BootLoader() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-6">
      <div className="pointer-events-none absolute inset-0" style={{ background: "var(--body-bg)" }} />
      <div className="relative flex w-full max-w-sm flex-col items-center text-center">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--accent)]">
          AI Job Hunter
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-[var(--heading)]">Abdul Wasay</h1>
        <div className="boot-spinner mt-8 h-10 w-10" aria-hidden />
        <span className="sr-only">Loading</span>
      </div>
    </div>
  );
}

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
    return <BootLoader />;
  }

  if (user?.auth_required && !user.authenticated) {
    return null;
  }

  return <>{children}</>;
}
