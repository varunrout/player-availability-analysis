import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output for a lean Cloud Run image (DEC-064).
  output: "standalone",
};

export default nextConfig;
