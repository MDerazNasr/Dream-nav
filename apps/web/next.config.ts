import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  reactStrictMode: true,
  transpilePackages: ["@dream-nav/shared", "@dream-nav/scene-registry"],
  async rewrites() {
    const apiBaseUrl = process.env.NEXT_PUBLIC_DREAMNAV_API_URL ?? "http://127.0.0.1:8000";
    return [
      {
        source: "/dreamnav-assets/:path*",
        destination: `${apiBaseUrl}/:path*`
      }
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Cross-Origin-Embedder-Policy",
            value: "require-corp"
          },
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin"
          }
        ]
      }
    ];
  }
};

export default nextConfig;
