"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
	deleteConversation,
	getConversationThread,
	listContentConversations,
} from "@/client/sdk.gen";
import type {
	ConversationMessageOut,
	ConversationSummary,
} from "@/client/types.gen";

export interface UseConversationOptions {
	contentId: number | null;
	initialConversationId?: string | null;
}

export interface UseConversationReturn {
	// Thread management
	summaries: ConversationSummary[];
	activeConversationId: string | null;
	setActiveConversationId: (id: string | null) => void;

	// Thread state
	messages: ConversationMessageOut[];
	modelUsed: string;

	// Loading states
	isInitializing: boolean;
	isLoadingThread: boolean;

	// Operations
	refreshSummaries: () => Promise<void>;
	deleteThread: (id: string, event: React.MouseEvent) => Promise<void>;

	// Errors
	error: string | null;
	clearError: () => void;

	// Reset state (for after sending messages)
	resetThreadState: () => void;
}

export function useConversation({
	contentId,
	initialConversationId = null,
}: UseConversationOptions): UseConversationReturn {
	const [summaries, setSummaries] = useState<ConversationSummary[]>([]);
	const [activeConversationId, setActiveConversationId] = useState<
		string | null
	>(initialConversationId);
	const [messages, setMessages] = useState<ConversationMessageOut[]>([]);
	const [modelUsed, setModelUsed] = useState<string>("");
	const [isInitializing, setIsInitializing] = useState(false);
	const [isLoadingThread, setIsLoadingThread] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const loadThreadReqIdRef = useRef(0);

	const clearError = useCallback(() => setError(null), []);

	const resetThreadState = useCallback(() => {
		setMessages([]);
		setModelUsed("");
	}, []);

	// Load conversation summaries when contentId changes
	useEffect(() => {
		if (!contentId) {
			setSummaries([]);
			setActiveConversationId(null);
			resetThreadState();
			return;
		}

		let cancelled = false;
		const loadSummaries = async () => {
			setIsInitializing(true);
			setError(null);
			const { data, error: apiError } = await listContentConversations({
				path: { content_id: contentId },
			});
			if (cancelled) return;

			if (data?.status === "success" && data.data) {
				const loadedSummaries = data.data;
				setSummaries(loadedSummaries);
				if (loadedSummaries.length === 0) {
					setActiveConversationId(null);
					resetThreadState();
				} else {
					// Only auto-select first conversation if none is currently selected
					// or if current selection is not in the new list
					setActiveConversationId((current) => {
						if (!current || !loadedSummaries.some((s) => s.id === current)) {
							return loadedSummaries[0].id;
						}
						return current;
					});
				}
			} else if (data?.message) {
				setError(data.message);
			} else if (apiError) {
				setError("Failed to load conversations");
			}
			setIsInitializing(false);
		};

		loadSummaries().catch((err) => {
			if (!cancelled) {
				setError(
					err instanceof Error ? err.message : "Failed to load conversations",
				);
				setIsInitializing(false);
			}
		});

		return () => {
			cancelled = true;
		};
	}, [contentId, resetThreadState]);

	// Refresh summaries
	const refreshSummaries = useCallback(async () => {
		if (!contentId) return;
		try {
			const { data } = await listContentConversations({
				path: { content_id: contentId },
			});
			if (data?.status === "success" && data.data) {
				const loadedSummaries = data.data;
				setSummaries(loadedSummaries);
				if (
					activeConversationId &&
					!loadedSummaries.some(
						(summary) => summary.id === activeConversationId,
					)
				) {
					setActiveConversationId(loadedSummaries[0]?.id ?? null);
				}
			}
		} catch (err) {
			console.error("Failed to refresh summaries:", err);
			setError(
				err instanceof Error ? err.message : "Failed to refresh conversations",
			);
		}
	}, [contentId, activeConversationId]);

	// Delete conversation thread
	const deleteThread = useCallback(
		async (conversationIdToDelete: string, event: React.MouseEvent) => {
			event.stopPropagation();
			if (!contentId || !conversationIdToDelete || isLoadingThread) return;

			if (
				!confirm(
					"Are you sure you want to delete this conversation thread? This action cannot be undone.",
				)
			) {
				return;
			}

			setIsLoadingThread(true);
			setError(null);
			try {
				const { data } = await deleteConversation({
					path: {
						content_id: contentId,
						conversation_id: conversationIdToDelete,
					},
				});
				if (data?.status === "success") {
					if (activeConversationId === conversationIdToDelete) {
						const remaining = summaries.filter(
							(s) => s.id !== conversationIdToDelete,
						);
						setActiveConversationId(remaining[0]?.id ?? null);
						resetThreadState();
					}
					await refreshSummaries();
				} else {
					setError(data?.message || "Failed to delete conversation");
				}
			} catch (err) {
				setError(
					err instanceof Error
						? err.message
						: "An unexpected error occurred while deleting the conversation.",
				);
			} finally {
				setIsLoadingThread(false);
			}
		},
		[
			contentId,
			activeConversationId,
			summaries,
			refreshSummaries,
			isLoadingThread,
			resetThreadState,
		],
	);

	// Load thread when activeConversationId changes
	useEffect(() => {
		if (!contentId || !activeConversationId) {
			return;
		}

		const reqId = ++loadThreadReqIdRef.current;
		setIsInitializing(true);
		setError(null);

		const loadThread = async () => {
			try {
				const { data, error: apiError } = await getConversationThread({
					path: {
						content_id: contentId,
						conversation_id: activeConversationId,
					},
				});
				if (reqId !== loadThreadReqIdRef.current) return;

				if (data?.status === "success" && data.data) {
					setMessages(data.data.messages);
					setModelUsed(data.data.model);
				} else if (data?.message) {
					if (
						data.message.includes("not found") ||
						data.message.includes("404")
					) {
						setError("Conversation not found. Refreshing list...");
						await refreshSummaries();
						setActiveConversationId(null);
					} else {
						setError(data.message);
					}
					setMessages([]);
				} else if (apiError) {
					setError("Failed to load conversation");
					setMessages([]);
				}
			} catch (err) {
				if (reqId !== loadThreadReqIdRef.current) return;
				setError(
					err instanceof Error ? err.message : "Failed to load conversation",
				);
				setMessages([]);
			} finally {
				if (reqId === loadThreadReqIdRef.current) {
					setIsInitializing(false);
				}
			}
		};

		loadThread();

		return () => {
			loadThreadReqIdRef.current++;
		};
	}, [contentId, activeConversationId, refreshSummaries]);

	return {
		summaries,
		activeConversationId,
		setActiveConversationId,
		messages,
		modelUsed,
		isInitializing,
		isLoadingThread,
		refreshSummaries,
		deleteThread,
		error,
		clearError,
		resetThreadState,
	};
}
