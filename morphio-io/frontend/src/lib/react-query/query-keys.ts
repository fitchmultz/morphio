/**
 * Centralized query key factory for consistent key structure across the app
 */

export const queryKeys = {
	// Auth related queries
	auth: {
		user: ["auth", "user"] as const,
		session: ["auth", "session"] as const,
	},

	// Templates related queries
	templates: {
		all: ["templates"] as const,
		byId: (id: number | string) => ["templates", id] as const,
	},

	// Contents related queries
	contents: {
		all: ["contents"] as const,
		paginated: (page: number, perPage: number) =>
			["contents", "paginated", { page, perPage }] as const,
		byTemplate: (templateId: number | string, page: number, perPage: number) =>
			["contents", "byTemplate", templateId, { page, perPage }] as const,
		byId: (id: number | string) => ["contents", id] as const,
	},

	// Media processing related queries
	media: {
		status: (jobId: string) => ["media", "status", jobId] as const,
		config: ["media", "config"] as const,
	},

	// Admin related queries
	admin: {
		usageStats: ["admin", "usageStats"] as const,
		subscriptions: ["admin", "subscriptions"] as const,
	},
};
