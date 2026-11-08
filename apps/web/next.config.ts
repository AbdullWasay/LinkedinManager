import type { NextConfig } from "next";

/**
 * Browser calls same-origin `/api/*` (first-party cookies).
 * Next rewrites those to the FastAPI host (local or Railway/Render).
 */
const apiProxyTarget = (
  process.env.API_PROXY_TARGET ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

// Rewrites are baked in at build time. On Vercel, localhost → DNS_HOSTNAME_RESOLVED_PRIVATE.
if (
  process.env.VERCEL &&
  /^(https?:\/\/)?(localhost|127\.0\.0\.1)(:|\/|$)/i.test(apiProxyTarget)
) {
  throw new Error(
    "Set API_PROXY_TARGET in Vercel to your public FastAPI URL (e.g. https://….onrender.com), then redeploy. Do not use localhost."
  );
}

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
