"use client";

import { forwardRef } from "react";
import { FiCpu, FiMessageSquare } from "react-icons/fi";
import type { ConversationMessageOut } from "@/client/types.gen";
import MessageBubble from "./MessageBubble";

interface MessageListProps {
	messages: ConversationMessageOut[];
	isLoading: boolean;
	isBusy: boolean;
	contentId: number | null;
}

const MessageList = forwardRef<HTMLDivElement, MessageListProps>(
	({ messages, isLoading, isBusy, contentId }, ref) => {
		if (!contentId) {
			return (
				<div className="flex flex-col items-center justify-center px-6 py-12 text-center">
					<div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 mb-4">
						<FiMessageSquare className="h-8 w-8 text-blue-500 dark:text-blue-400" />
					</div>
					<p className="morphio-body font-medium text-gray-700 dark:text-gray-300">
						Save this content to start iterating
					</p>
					<p className="morphio-caption mt-1 text-gray-500 dark:text-gray-400">
						with the conversation assistant
					</p>
				</div>
			);
		}

		return (
			<div className="flex-1 overflow-y-auto px-6 py-6 space-y-6" ref={ref}>
				{isLoading && messages.length === 0 ? (
					<div className="space-y-6">
						{[1, 2, 3].map((i) => (
							<div key={i} className="flex gap-3">
								<div className="h-10 w-10 flex-shrink-0 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700" />
								<div className="flex-1 space-y-2">
									<div className="h-4 w-24 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700" />
									<div className="h-20 w-full animate-pulse rounded-2xl bg-gray-200 dark:bg-gray-700" />
								</div>
							</div>
						))}
					</div>
				) : messages.length === 0 ? (
					<div className="flex h-full flex-col items-center justify-center text-center py-12">
						<div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 mb-4">
							<FiCpu className="h-8 w-8 text-blue-500 dark:text-blue-400" />
						</div>
						<p className="morphio-body font-medium text-gray-700 dark:text-gray-300">
							No conversation history yet
						</p>
						<p className="morphio-caption mt-1 text-gray-500 dark:text-gray-400">
							Ask the assistant to refine this content
						</p>
					</div>
				) : (
					<div className="flex flex-col gap-6">
						{messages.map((message) => (
							<MessageBubble
								key={`${message.id}-${message.created_at}`}
								message={message}
							/>
						))}
						{isBusy && (
							<div className="flex gap-3 justify-start">
								<div className="flex-shrink-0">
									<div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-500 shadow-lg">
										<FiCpu className="h-5 w-5 text-white" />
									</div>
								</div>
								<div className="flex items-center gap-2 px-5 py-4 bg-white dark:bg-slate-800 rounded-2xl border border-gray-200 dark:border-slate-700">
									<div className="flex gap-1">
										<div className="h-2 w-2 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.3s]" />
										<div className="h-2 w-2 animate-bounce rounded-full bg-purple-500 [animation-delay:-0.15s]" />
										<div className="h-2 w-2 animate-bounce rounded-full bg-blue-500" />
									</div>
									<span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
										Thinking...
									</span>
								</div>
							</div>
						)}
					</div>
				)}
			</div>
		);
	},
);

MessageList.displayName = "MessageList";

export default MessageList;
