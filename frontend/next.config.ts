import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/flashcards", destination: "/today", permanent: false },
      { source: "/profile", destination: "/settings", permanent: false },
      { source: "/verify-email-change-step1/:token", destination: "/settings", permanent: false },
      { source: "/verify-email-change-step2/:token", destination: "/settings", permanent: false },
    ];
  },
  webpack: (config) => {
    // Handle D3 modules properly
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
    };
    
    // Ensure proper module resolution for D3
    config.module.rules.push({
      test: /\.m?js$/,
      resolve: {
        fullySpecified: false,
      },
    });
    
    return config;
  },
};

export default nextConfig;

