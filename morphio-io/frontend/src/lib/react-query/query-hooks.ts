"use client";

import {
	type QueryKey,
	type UseMutationOptions,
	type UseQueryOptions,
	useMutation,
	useQuery,
} from "@tanstack/react-query";

/**
 * Generic API response type matching the generated client pattern
 */
interface ApiResponse<T> {
	status: string;
	message?: string;
	data?: T | null;
}

/**
 * Base hook for API queries with error handling for Morphio API responses
 */
export function useApiQuery<TData = unknown, TError = unknown>(
	queryKey: QueryKey,
	fetchFn: () => Promise<ApiResponse<TData>>,
	options?: Omit<
		UseQueryOptions<ApiResponse<TData>, TError, TData>,
		"queryKey" | "queryFn"
	>,
) {
	return useQuery({
		queryKey,
		queryFn: fetchFn,
		select: (data) => {
			if (data.status === "success") {
				return data.data;
			}
			throw new Error(data.message || "An unknown error occurred");
		},
		...options,
	});
}

/**
 * Base hook for API mutations with error handling
 */
export function useApiMutation<
	TData = unknown,
	TVariables = unknown,
	TError = unknown,
>(
	mutationFn: (variables: TVariables) => Promise<ApiResponse<TData>>,
	options?: Omit<
		UseMutationOptions<ApiResponse<TData>, TError, TVariables, unknown>,
		"mutationFn"
	>,
) {
	return useMutation({
		mutationFn,
		...options,
	});
}
