import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    // One public port (Replit). Everything under /api is proxied to FastAPI.
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/:path*` }];
  },
};

export default nextConfig;
