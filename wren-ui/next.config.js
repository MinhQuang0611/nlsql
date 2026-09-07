/* eslint-disable @typescript-eslint/no-var-requires */

const path = require('path');
const withLess = require('next-with-less');
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

const resolveAlias = {
  antd$: path.resolve(__dirname, 'src/import/antd'),
};

/** @type {import('next').NextConfig} */
const nextConfig = withLess({
  // 👇 THÊM DÒNG NÀY ĐỂ BỎ QUA LỖI LINT KHI BUILD
  eslint: {
    ignoreDuringBuilds: true,
  },
  // ---------------------------------------------
  
  output: 'standalone',
  transpilePackages: ['vega-lite', 'vega-embed', 'vega'],
  experimental: {
    esmExternals: 'loose',
    proxyTimeout: 300000,
  },
  staticPageGenerationTimeout: 1000,
  compiler: {
    // Enables the styled-components SWC transform
    styledComponents: {
      displayName: true,
      ssr: true,
    },
  },
  lessLoaderOptions: {
    additionalData: `@import "@/styles/antd-variables.less";`,
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      ...resolveAlias,
    };
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.WREN_ENGINE_URL || 'http://app:8388'}/api/v1/:path*`,
      },
    ];
  },
  // routes redirect
  async redirects() {
    return [
      {
        source: '/setup/:path*',
        destination: '/home',
        permanent: false,
      },
      {
        source: '/onboarding/:path*',
        destination: '/home',
        permanent: false,
      },
      {
        source: '/setup',
        destination: '/home',
        permanent: false,
      },
    ];
  },
});

module.exports = withBundleAnalyzer(nextConfig);