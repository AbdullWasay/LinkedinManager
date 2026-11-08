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
