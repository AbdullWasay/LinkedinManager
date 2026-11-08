import type { NextConfig } from "next";

/**
 * Browser calls same-origin `/api/*` (first-party cookies).
 * Next rewrites those to the FastAPI host (local or Railway/Render).
 */
const rawProxyTarget = (
  process.env.API_PROXY_TARGET ||
  process.env.NEXT_PUBLIC_API_URL ||
  ""
).replace(/\/$/, "");

const isPrivateHost = /^(https?:\/\/)?(localhost|127\.0\.0\.1)(:|\/|$)/i.test(
  rawProxyTarget
);

// Rewrites are baked in at build time. Never proxy Vercel → localhost (DNS_HOSTNAME_RESOLVED_PRIVATE).
const apiProxyTarget =
  process.env.VERCEL && (!rawProxyTarget || isPrivateHost)
    ? ""
    : rawProxyTarget || "http://localhost:8000";

if (process.env.VERCEL && !apiProxyTarget) {
  console.warn(
    "[next.config] API_PROXY_TARGET is missing or points at localhost. Set it to your public FastAPI URL so /api/* login works."
  );
}

const nextConfig: NextConfig = {
  async rewrites() {
    if (!apiProxyTarget) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
