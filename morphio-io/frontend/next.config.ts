// @ts-check
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	productionBrowserSourceMaps: false,
	webpack: (config, { isServer, dev }) => {
		if (!isServer) {
			config.resolve.fallback = {
				...config.resolve.fallback,
				punycode: false,
			};
		}
		// Enable polling for Docker development (file watching in containers)
		if (dev) {
			config.watchOptions = {
				poll: 1000,
				aggregateTimeout: 300,
				ignored: /node_modules/,
			};
		}
		return config;
	},
	turbopack: {},
	env: {
		NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
	},
	reactStrictMode: false,
	poweredByHeader: false,
	compress: true,
	images: {
		remotePatterns: [
			{
				protocol: "https",
				hostname: "morphio.io",
			},
		],
		formats: ["image/avif", "image/webp"],
	},
	// Removed i18n config as it's not compatible with App Router
	rewrites: async () => {
		if (process.env.NODE_ENV === "development") {
			return [
				{
					source: "/backend-api/:path*",
					destination: "http://localhost:8000/:path*",
				},
			];
		}
		return [];
	},
};

export default nextConfig;
