"use client";

import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { FiChevronDown, FiChevronUp } from "react-icons/fi";
// Hooks
import { useChatForm } from "@/hooks/useChatForm";
import { useChatMessages } from "@/hooks/useChatMessages";
import { useConversation } from "@/hooks/useConversation";
import { useSuggestions } from "@/hooks/useSuggestions";
import { cn } from "@/lib/cn";

// Components
import ContentDisplay from "./ContentDisplay";
import {
	ChangeSummaryPanel,
	ChatHeader,
	ChatInputForm,
	ConversationThreadList,
	MessageList,
	QuickSuggestions,
} from "./chat";

interface ContentWithChatProps {
	content: string;
	contentId?: number | null;
	title?: string;
	templateName?: string | null;
	conversationId?: string | null;
	className?: string;
	showContentAsCard?: boolean;
	onContentUpdate?: (content: string, changeSummary: string[]) => void;
	onRefreshRequested?: () => void;
}

const ContentWithChat: React.FC<ContentWithChatProps> = ({
	content,
	contentId = null,
	title,
	templateName,
	conversationId = null,
	className,
	showContentAsCard = true,
	onContentUpdate,
	onRefreshRequested,
}) => {
	// UI state
	const [isChatOpen, setIsChatOpen] = useState(true);
	const [displayContent, setDisplayContent] = useState(content);
	const [changeSummary, setChangeSummary] = useState<string[]>([]);
	const [notes, setNotes] = useState<string | null>(null);
	const [serverSuggestions, setServerSuggestions] = useState<string[]>([]);

	const listRef = useRef<HTMLDivElement | null>(null);

	// Sync content when prop changes
	useEffect(() => {
		setDisplayContent(content);
	}, [content]);

	// Conversation management
	const conversation = useConversation({
		contentId,
		initialConversationId: conversationId,
	});

	// Message sending
	const chatMessages = useChatMessages({
		contentId,
		activeConversationId: conversation.activeConversationId,
		onSuccess: (response) => {
			setDisplayContent(response.updated_content);
			setChangeSummary(response.change_summary || []);
			setNotes(response.notes || null);
			setServerSuggestions(response.suggestions || []);
			onContentUpdate?.(
				response.updated_content,
				response.change_summary || [],
			);
			conversation.refreshSummaries();
			onRefreshRequested?.();
			form.clearInput();
		},
		onConversationCreated: conversation.setActiveConversationId,
	});

	// Suggestions
	const { quickActions } = useSuggestions({
		content: displayContent,
		serverSuggestions:
			serverSuggestions.length > 0 ? serverSuggestions : undefined,
	});

	// Reset suggestions when conversation changes and no active conversation
	useEffect(() => {
		if (!conversation.activeConversationId) {
			setServerSuggestions([]);
			setChangeSummary([]);
			setNotes(null);
		}
	}, [conversation.activeConversationId]);

	// Form handling
	const handleSendMessage = useCallback(
		async (message: string) => {
			await chatMessages.sendMessage(message);
		},
		[chatMessages],
	);

	const form = useChatForm({
		maxLength: 5000,
		onSubmit: handleSendMessage,
	});

	// Handle suggestion click
	const handleSuggestionClick = useCallback(
		(suggestion: string) => {
			chatMessages.sendMessage(suggestion, suggestion);
		},
		[chatMessages],
	);

	// Combined busy state
	const isBusy = chatMessages.isSending || conversation.isLoadingThread;
	const error = conversation.error || chatMessages.error;

	// Scroll to bottom when messages change
	useEffect(() => {
		if (listRef.current) {
			listRef.current.scrollTop = listRef.current.scrollHeight;
		}
	});

	return (
		<div className={cn("space-y-4", className)}>
			{/* Mobile toggle button */}
			<div className="flex justify-end lg:hidden">
				<button
					type="button"
					onClick={() => setIsChatOpen((open) => !open)}
					className="morphio-button-secondary flex items-center gap-2"
				>
					{isChatOpen ? (
						<>
							<FiChevronUp className="h-4 w-4" />
							Hide Conversation
						</>
					) : (
						<>
							<FiChevronDown className="h-4 w-4" />
							Show Conversation
						</>
					)}
				</button>
			</div>

			<div className="flex flex-col gap-6 lg:flex-row">
				<div className="lg:flex-1">
					<ContentDisplay
						content={displayContent}
						title={title}
						showCopyButton
						showAsCard={showContentAsCard}
					/>
				</div>

				<aside
					className={cn(
						"lg:w-[32rem] lg:min-w-[32rem]",
						isChatOpen ? "block" : "hidden lg:block",
					)}
				>
					<div className="morphio-card h-full flex flex-col max-h-[calc(100vh-8rem)]">
						<ChatHeader
							templateName={templateName}
							modelUsed={conversation.modelUsed}
							onRefresh={conversation.refreshSummaries}
							isRefreshing={isBusy}
							isDisabled={!contentId || isBusy}
						/>

						<ChangeSummaryPanel changeSummary={changeSummary} notes={notes} />

						<ConversationThreadList
							summaries={conversation.summaries}
							activeConversationId={conversation.activeConversationId}
							onSelectThread={conversation.setActiveConversationId}
							onDeleteThread={conversation.deleteThread}
							isDisabled={isBusy}
						/>

						<MessageList
							ref={listRef}
							messages={conversation.messages}
							isLoading={conversation.isInitializing}
							isBusy={chatMessages.isSending}
							contentId={contentId}
						/>

						{error && (
							<div className="mx-6 mb-4 rounded-lg border border-red-200 bg-red-50/80 px-4 py-3 dark:border-red-800/50 dark:bg-red-900/20">
								<p className="text-sm font-medium text-red-700 dark:text-red-400">
									{error}
								</p>
							</div>
						)}

						<QuickSuggestions
							suggestions={quickActions}
							onSuggestionClick={handleSuggestionClick}
							isDisabled={isBusy || !contentId}
						/>

						<ChatInputForm
							value={form.inputValue}
							onChange={form.handleChange}
							onSubmit={form.handleSubmit}
							isDisabled={isBusy}
							contentId={contentId}
							maxLength={5000}
							isNearLimit={form.isNearLimit}
							charactersRemaining={form.charactersRemaining}
						/>
					</div>
				</aside>
			</div>
		</div>
	);
};

export default ContentWithChat;
