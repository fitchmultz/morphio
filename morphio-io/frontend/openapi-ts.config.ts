import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
	input: "./openapi.json",
	output: {
		path: "src/client",
		format: "prettier",
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
