/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  serverComponentsExternalPackages: ['yahoo-finance2'],
}

export default nextConfig

export default nextConfig
