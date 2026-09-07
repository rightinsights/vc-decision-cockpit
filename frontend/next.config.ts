import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    // One public port. Everything under /api is proxied to FastAPI.
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/:path*` }];
  },
  experimental: {
    // Deck analysis, research, and the agent check are synchronous and take 1 to 3 minutes.
    // The default rewrite proxy timeout is 30 s, which turns them into 500s.
    proxyTimeout: 15 * 60 * 1000,
  },
};

export default nextConfig;
