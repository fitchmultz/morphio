/**
 * Purpose: Configure frontend OpenAPI client generation from the backend schema.
 * Responsibilities: Define generator input, output, and plugin behavior for typed client code.
 * Scope: Source-of-truth generation settings for `pnpm openapi:generate`.
 * Usage: Consumed by `@hey-api/openapi-ts` during local and CI regeneration.
 * Invariants/Assumptions: Generated output must match repository Biome formatting rules without manual edits.
 */
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
	input: "./openapi.json",
	output: {
		path: "src/client",
		postProcess: ["biome:format"],
	},
	plugins: [
		"@hey-api/typescript",
		{
			name: "@hey-api/client-next",
			throwOnError: false,
		},
		{
			name: "@hey-api/sdk",
			operations: {
				strategy: "flat",
			},
		},
		{
			name: "@tanstack/react-query",
			queryOptions: true,
			queryKeys: true,
		},
	],
});
