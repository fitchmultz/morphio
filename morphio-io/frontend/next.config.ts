// @ts-check
import type { NextConfig } from "next";
import fs from "node:fs";
import path from "node:path";

const envRoot = path.resolve(__dirname, "..", "..");
const envFiles = [".env"].map((name) => path.join(envRoot, name));

const loadEnvFile = (filePath: string, override = false) => {
	if (!fs.existsSync(filePath)) return;
	const contents = fs.readFileSync(filePath, "utf-8");
	for (const rawLine of contents.split(/\r?\n/)) {
		const line = rawLine.trim();
		if (!line || line.startsWith("#") || !line.includes("=")) {
			continue;
		}
		const [key, ...rest] = line.split("=");
		const value = rest.join("=").trim();
		if (!key) continue;
		if (!override && process.env[key] !== undefined) continue;
		const normalized =
			value.startsWith("\"") && value.endsWith("\"")
				? value.slice(1, -1)
				: value;
		process.env[key] = normalized;
	}
};

loadEnvFile(envFiles[0]);

const nextConfig: NextConfig = {
	productionBrowserSourceMaps: false,
	allowedDevOrigins: ["127.0.0.1", "localhost"],
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
	reactStrictMode: true,
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
					destination: "http://localhost:8005/:path*",
				},
			];
		}
		return [];
	},
};

export default nextConfig;
