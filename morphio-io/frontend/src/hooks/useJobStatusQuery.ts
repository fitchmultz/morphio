"use client";

import { useQuery } from "@tanstack/react-query";
import {
	getLogsProcessingStatus,
	getMediaProcessingStatus,
	getWebProcessingStatus,
} from "@/client/sdk.gen";
import type {
	LogsProcessingStatusResponse,
	MediaProcessingStatusResponse,
} from "@/client/types.gen";

// Unified status type that covers both media and logs processing
export type UnifiedProcessingStatus =
	| MediaProcessingStatusResponse
	| LogsProcessingStatusResponse;

export function useJobStatusQuery(
	jobId: string | null,
	isWebProcessing: boolean = false,
	isLogProcessing: boolean = false,
) {
	const jobStatusQuery = useQuery({
		queryKey: ["jobStatus", jobId, isWebProcessing, isLogProcessing],
		queryFn: async (): Promise<UnifiedProcessingStatus> => {
			if (!jobId) {
				throw new Error("Job ID is required");
			}

			if (isLogProcessing) {
				const response = await getLogsProcessingStatus({
					path: { job_id: jobId },
				});
				// Return the inner data, not the wrapper
				if (response.data?.data) return response.data.data;
				throw new Error("Failed to fetch job status");
			}

			if (isWebProcessing) {
				const response = await getWebProcessingStatus({
					path: { job_id: jobId },
				});
				if (response.data) return response.data;
				throw new Error("Failed to fetch job status");
			}

			const response = await getMediaProcessingStatus({
				path: { job_id: jobId },
			});
			if (response.data) return response.data;
			throw new Error("Failed to fetch job status");
		},
		enabled: !!jobId,
		refetchInterval: (query) => {
			const data = query.state.data;
			// Stop polling if job is completed or failed
			if (data?.status === "completed" || data?.status === "failed") {
				return false;
			}
			// Poll every 2 seconds
			return 2000;
		},
	});

	return {
		status: jobStatusQuery.data || null,
		error: jobStatusQuery.error ? String(jobStatusQuery.error) : null,
		isLoading: jobStatusQuery.isLoading,
	};
}

// Re-export types for consumers
export type {
	JobStatus,
	LogsProcessingStatusResponse,
	MediaProcessingStatusResponse,
} from "@/client/types.gen";
