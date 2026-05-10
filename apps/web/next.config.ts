import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@dream-nav/shared", "@dream-nav/scene-registry"],
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
