"use client";

import { useCallback, useRef, useState } from "react";
import { continueConversation } from "@/client/sdk.gen";
import type {
	ConversationMessageOut,
	ConversationRequest,
	ConversationResponse,
} from "@/client/types.gen";

export interface UseChatMessagesOptions {
	contentId: number | null;
	activeConversationId: string | null;
	onSuccess?: (response: ConversationResponse) => void;
	onConversationCreated?: (id: string) => void;
	onMessagesUpdated?: (messages: ConversationMessageOut[]) => void;
}

export interface ChatResponse {
	updatedContent: string;
	changeSummary: string[];
	notes: string | null;
	suggestions: string[];
	messages: ConversationMessageOut[];
	modelUsed: string;
	conversationId: string;
}

export interface UseChatMessagesReturn {
	sendMessage: (message: string, followUpType?: string) => Promise<void>;
	isSending: boolean;
	error: string | null;
	clearError: () => void;
	lastResponse: ChatResponse | null;
}

export function useChatMessages({
	contentId,
	activeConversationId,
	onSuccess,
	onConversationCreated,
	onMessagesUpdated,
}: UseChatMessagesOptions): UseChatMessagesReturn {
	const [isSending, setIsSending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);

	// Synchronous lock to prevent double-send race conditions
	const busyLockRef = useRef(false);

	const clearError = useCallback(() => setError(null), []);

	const sendMessage = useCallback(
		async (message: string, followUpType?: string) => {
			const trimmed = message.trim();
			if (!trimmed || !contentId || busyLockRef.current) {
				return;
			}

			if (trimmed.length > 5000) {
				setError("Message is too long. Maximum 5000 characters allowed.");
				return;
			}

			busyLockRef.current = true;
			setIsSending(true);
			setError(null);

			try {
				const payload: ConversationRequest = {
					message: trimmed,
					preserve_context: true,
					conversation_id: activeConversationId ?? undefined,
					follow_up_type: followUpType,
				};

				const { data, error: apiError } = await continueConversation({
					path: { content_id: contentId },
					body: payload,
				});

				if (data?.status === "success" && data.data) {
					const responseData: ConversationResponse = data.data;

					const chatResponse: ChatResponse = {
						updatedContent: responseData.updated_content,
						changeSummary: responseData.change_summary || [],
						notes: responseData.notes || null,
						suggestions: responseData.suggestions || [],
						messages: responseData.messages,
						modelUsed: responseData.model_used,
						conversationId: responseData.conversation_id,
					};

					setLastResponse(chatResponse);
					onMessagesUpdated?.(responseData.messages);
					onConversationCreated?.(responseData.conversation_id);
					onSuccess?.(responseData);
				} else {
					if (
						data?.message?.includes("not found") ||
						data?.message?.includes("404")
					) {
						setError(
							"The conversation was not found. Starting a new conversation.",
						);
					} else {
						setError(
							data?.message ||
								apiError?.toString() ||
								"Failed to continue conversation",
						);
					}
				}
			} catch (err) {
				setError(
					err instanceof Error
						? err.message
						: "An unexpected error occurred while sending the message.",
				);
			} finally {
				busyLockRef.current = false;
				setIsSending(false);
			}
		},
		[
			contentId,
			activeConversationId,
			onSuccess,
			onConversationCreated,
			onMessagesUpdated,
		],
	);

	return {
		sendMessage,
		isSending,
		error,
		clearError,
		lastResponse,
	};
}
