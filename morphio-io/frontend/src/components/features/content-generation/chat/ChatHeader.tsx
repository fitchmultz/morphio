"use client";

import type React from "react";
import { memo } from "react";
import { FiMessageSquare, FiRefreshCcw } from "react-icons/fi";
import { cn } from "@/lib/cn";

interface ChatHeaderProps {
	templateName?: string | null;
	modelUsed: string;
	onRefresh: () => void;
	isRefreshing: boolean;
	isDisabled: boolean;
}

const ChatHeader: React.FC<ChatHeaderProps> = memo(
	({ templateName, modelUsed, onRefresh, isRefreshing, isDisabled }) => {
		return (
			<div className="flex items-center justify-between border-b border-slate-200/60 px-6 py-5 dark:border-slate-700/60 bg-gradient-to-r from-blue-50/30 via-purple-50/20 to-transparent dark:from-slate-800/50 dark:via-slate-800/30">
				<div className="flex items-center gap-3">
					<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 shadow-lg">
						<FiMessageSquare className="h-5 w-5 text-white" />
					</div>
					<div>
						<h3 className="morphio-h4">Conversation Studio</h3>
						<p className="morphio-caption text-slate-500 dark:text-slate-400 mt-0.5">
							{templateName ? `${templateName}` : "No template"} ·{" "}
							{modelUsed || "—"}
						</p>
					</div>
				</div>
				<button
					type="button"
					onClick={onRefresh}
					disabled={isDisabled}
					className="morphio-icon-button hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300"
					title="Refresh conversations"
					aria-label="Refresh conversations"
				>
					<FiRefreshCcw
						className={cn("h-4 w-4", isRefreshing && "animate-spin")}
					/>
				</button>
			</div>
		);
	},
);

ChatHeader.displayName = "ChatHeader";

export default ChatHeader;
