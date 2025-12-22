"use client";

import { formatDistanceToNow, parseISO } from "date-fns";
import dynamic from "next/dynamic";
import type React from "react";
import { memo } from "react";
import { FiClock, FiCpu, FiUser } from "react-icons/fi";
import remarkGfm from "remark-gfm";
import type { ConversationMessageOut } from "@/client/types.gen";
import { cn } from "@/lib/cn";

const ReactMarkdown = dynamic(() => import("react-markdown"), { ssr: false });

interface MessageBubbleProps {
	message: ConversationMessageOut;
}

const MessageBubble: React.FC<MessageBubbleProps> = memo(({ message }) => {
	const isAssistant = message.role === "assistant";
	const timestamp = parseISO(message.created_at);
	const readableTime = Number.isNaN(timestamp.getTime())
		? ""
		: formatDistanceToNow(timestamp, { addSuffix: true });

	return (
		<div
			className={cn(
				"flex gap-3",
				isAssistant ? "justify-start" : "justify-end",
			)}
		>
			{isAssistant && (
				<div className="flex-shrink-0">
					<div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-500 shadow-lg">
						<FiCpu className="h-5 w-5 text-white" />
					</div>
				</div>
			)}
			<div
				className="flex flex-col gap-1"
				style={{ maxWidth: "calc(100% - 4rem)" }}
			>
				<div className="flex items-center gap-2 mb-1">
					<span
						className={cn(
							"text-xs font-semibold",
							isAssistant
								? "text-blue-600 dark:text-blue-400"
								: "text-gray-600 dark:text-gray-400",
						)}
					>
						{isAssistant ? "Morphio AI" : "You"}
					</span>
					{readableTime && (
						<span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
							<FiClock className="h-3 w-3" />
							{readableTime}
						</span>
					)}
				</div>
				<div
					className={cn(
						"rounded-2xl px-5 py-4 shadow-md transition-all duration-200",
						isAssistant
							? "bg-white text-gray-900 dark:bg-slate-800 dark:text-slate-100 border border-gray-200 dark:border-slate-700"
							: "bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg",
					)}
				>
					<div
						className={cn(
							"prose prose-sm max-w-none leading-relaxed",
							isAssistant
								? "prose-gray dark:prose-invert"
								: "prose-invert prose-white",
							"prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-headings:my-3",
						)}
					>
						<ReactMarkdown remarkPlugins={[remarkGfm]}>
							{message.content}
						</ReactMarkdown>
					</div>
				</div>
			</div>
			{!isAssistant && (
				<div className="flex-shrink-0">
					<div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-700 shadow-md">
						<FiUser className="h-5 w-5 text-gray-600 dark:text-gray-300" />
					</div>
				</div>
			)}
		</div>
	);
});

MessageBubble.displayName = "MessageBubble";

export default MessageBubble;
