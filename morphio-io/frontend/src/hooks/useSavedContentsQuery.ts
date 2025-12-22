"use client";

import { useQuery } from "@tanstack/react-query";
import {
	listContentsOptions,
	listTemplatesOptions,
} from "@/client/@tanstack/react-query.gen";
import type {
	ContentOut,
	PaginatedResponseContentOut,
} from "@/client/types.gen";
import { useAuth } from "@/contexts/AuthContext";

const emptyResponse: PaginatedResponseContentOut = {
	items: [],
	total: 0,
	page: 1,
	per_page: 10,
};

export function useSavedContentsQuery(
	page: number,
	perPage: number,
	templateIdOrName?: string | number,
) {
	const { isAuthenticated, loading } = useAuth();

	// Query for resolving template name to ID if needed
	const templatesQuery = useQuery({
		...listTemplatesOptions(),
		enabled:
			isAuthenticated && !loading && typeof templateIdOrName === "string",
		staleTime: 1000 * 60 * 5, // 5 minutes
	});

	// Resolve template ID from name if needed
	let resolvedTemplateId: number | undefined;
	if (typeof templateIdOrName === "number") {
		resolvedTemplateId = templateIdOrName;
	} else if (
		typeof templateIdOrName === "string" &&
		templatesQuery.data?.status === "success" &&
		templatesQuery.data.data
	) {
		const templates = templatesQuery.data.data;
		const template = templates.find((t) => t.name === templateIdOrName);
		resolvedTemplateId = template?.id;
	}

	// Main query for saved contents
	const contentsQuery = useQuery({
		...listContentsOptions({
			query: {
				page,
				per_page: perPage,
				template_id: resolvedTemplateId,
			},
		}),
		select: (response) => {
			if (response.status === "success" && response.data) {
				return response.data;
			}
			return { ...emptyResponse, page, per_page: perPage };
		},
		enabled:
			isAuthenticated &&
			!loading &&
			(typeof templateIdOrName !== "string" ||
				templatesQuery.isSuccess ||
				templatesQuery.isError),
	});

	return {
		data: contentsQuery.data || { ...emptyResponse, page, per_page: perPage },
		isLoading:
			loading ||
			contentsQuery.isLoading ||
			(typeof templateIdOrName === "string" && templatesQuery.isLoading),
		error: contentsQuery.error ? String(contentsQuery.error) : null,
		refetch: contentsQuery.refetch,
	};
}

// Re-export types for consumers
export type { ContentOut, PaginatedResponseContentOut };
