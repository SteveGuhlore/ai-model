/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Proxy API + media to the FastAPI backend so the browser never needs a key
  // and there is no CORS dance in dev. Override the target via API_PROXY_TARGET.
  async rewrites() {
    const target = process.env.API_PROXY_TARGET || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${target}/:path*` },
      { source: "/media/:path*", destination: `${target}/media/:path*` },
    ];
  },
};

export default nextConfig;
