"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
	getLogsProcessingStatus,
	getMediaProcessingStatus,
	getWebProcessingStatus,
} from "@/client/sdk.gen";
import type {
	LogsProcessingStatusResponse,
	MediaProcessingStatusResponse,
} from "@/client/types.gen";
import { API_BASE_URL } from "@/utils/constants";

// Unified status type that covers both media and logs processing
export type UnifiedProcessingStatus =
	| MediaProcessingStatusResponse
	| LogsProcessingStatusResponse;

export function useJobStatusQuery(
	jobId: string | null,
	isWebProcessing: boolean = false,
	isLogProcessing: boolean = false,
) {
	const [wsStatus, setWsStatus] = useState<UnifiedProcessingStatus | null>(
		null,
	);
	const [wsError, setWsError] = useState<string | null>(null);
	const [usePolling, setUsePolling] = useState(false);

	useEffect(() => {
		if (!jobId) {
			setWsStatus(null);
			setWsError(null);
			setUsePolling(false);
			return;
		}

		if (typeof WebSocket === "undefined") {
			setUsePolling(true);
			return;
		}

		const token = localStorage.getItem("access_token");
		if (!token) {
			setUsePolling(true);
			return;
		}

		const wsBaseUrl = API_BASE_URL.replace(/^http/, "ws");
		const wsUrl = new URL(`/ws/job-status/${jobId}`, wsBaseUrl);
		wsUrl.searchParams.set("token", token);

		let closedOnTerminal = false;
		let socket: WebSocket | null = null;

		setUsePolling(false);
		setWsError(null);
		setWsStatus(null);

		try {
			socket = new WebSocket(wsUrl.toString());
		} catch (error) {
			setWsError(String(error));
			setUsePolling(true);
			return;
		}

		socket.onmessage = (event) => {
			try {
				const payload = JSON.parse(event.data) as UnifiedProcessingStatus;
				setWsStatus(payload);
				if (
					payload.status === "completed" ||
					payload.status === "failed" ||
					payload.status === "cancelled"
				) {
					closedOnTerminal = true;
					socket?.close();
				}
			} catch (error) {
				setWsError(String(error));
				setUsePolling(true);
			}
		};

		socket.onerror = () => {
			setWsError("WebSocket error");
			setUsePolling(true);
		};

		socket.onclose = () => {
			if (!closedOnTerminal) {
				setUsePolling(true);
			}
		};

		return () => {
			closedOnTerminal = true;
			socket?.close();
		};
	}, [jobId]);

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
				if (response.data?.data) return response.data.data;
				throw new Error("Failed to fetch job status");
			}

			const response = await getMediaProcessingStatus({
				path: { job_id: jobId },
			});
			if (response.data?.data) return response.data.data;
			throw new Error("Failed to fetch job status");
		},
		enabled: !!jobId && usePolling,
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
		status: wsStatus || jobStatusQuery.data || null,
		error:
			wsError || (jobStatusQuery.error ? String(jobStatusQuery.error) : null),
		isLoading: usePolling ? jobStatusQuery.isLoading : !wsStatus && !wsError,
	};
}

// Re-export types for consumers
export type {
	JobStatus,
	LogsProcessingStatusResponse,
	MediaProcessingStatusResponse,
} from "@/client/types.gen";
