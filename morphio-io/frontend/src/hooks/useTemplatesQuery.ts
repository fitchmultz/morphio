"use client";

import { useQuery } from "@tanstack/react-query";
import {
	listTemplatesOptions,
	listTemplatesQueryKey,
} from "@/client/@tanstack/react-query.gen";
import type { TemplateOut } from "@/client/types.gen";
import { useAuth } from "@/contexts/AuthContext";

export interface TemplateGroups {
	custom: TemplateOut[];
	default: TemplateOut[];
}

const emptyTemplateGroups: TemplateGroups = {
	custom: [],
	default: [],
};

export function useTemplatesQuery() {
	const { isAuthenticated, loading } = useAuth();

	const templatesQuery = useQuery({
		...listTemplatesOptions(),
		enabled: isAuthenticated && !loading,
		select: (response) => {
			if (response.status !== "success" || !response.data) {
				return emptyTemplateGroups;
			}

			const templates = response.data;
			return {
				custom: templates.filter((template) => !template.is_default),
				default: templates.filter((template) => template.is_default),
			};
		},
		retry: 3,
		retryDelay: 1000,
		staleTime: 60000, // 1 minute
	});

	return {
		data: templatesQuery.data || emptyTemplateGroups,
		isLoading: loading || templatesQuery.isLoading,
		error: templatesQuery.error ? String(templatesQuery.error) : null,
		refetch: templatesQuery.refetch,
	};
}

// Export query key for cache invalidation
export const templatesQueryKey = listTemplatesQueryKey;
