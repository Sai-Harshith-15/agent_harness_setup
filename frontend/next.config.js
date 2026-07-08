/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Proxy /api/* to the Context Server so the browser avoids CORS + self-signed cert pain.
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:27180/:path*" },
    ];
  },
};
module.exports = nextConfig;
