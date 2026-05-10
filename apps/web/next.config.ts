import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@dream-nav/shared", "@dream-nav/scene-registry"]
};

export default nextConfig;
