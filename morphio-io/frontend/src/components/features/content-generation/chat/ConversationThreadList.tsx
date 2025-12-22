"use client";

import { formatDistanceToNow, parseISO } from "date-fns";
import type React from "react";
import { memo } from "react";
import { FiTrash2 } from "react-icons/fi";
import type { ConversationSummary } from "@/client/types.gen";
import { cn } from "@/lib/cn";

interface ConversationThreadListProps {
	summaries: ConversationSummary[];
	activeConversationId: string | null;
	onSelectThread: (id: string) => void;
	onDeleteThread: (id: string, event: React.MouseEvent) => void;
	isDisabled: boolean;
}

const ConversationThreadList: React.FC<ConversationThreadListProps> = memo(
	({
		summaries,
		activeConversationId,
		onSelectThread,
		onDeleteThread,
		isDisabled,
	}) => {
		if (summaries.length <= 1) {
			return null;
		}

		return (
			<div className="border-b border-slate-200/60 px-6 py-3 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30">
				<span className="morphio-overline mb-2 block">
					Conversation Threads
				</span>
				<div className="flex flex-col gap-2 max-h-32 overflow-y-auto">
					{summaries.map((summary, index) => {
						const referenceDate = summary.updated_at || summary.created_at;
						let relative = "";
						try {
							relative = formatDistanceToNow(parseISO(referenceDate), {
								addSuffix: true,
							});
						} catch {
							relative = "";
						}
						const isActive = activeConversationId === summary.id;

						return (
							<div
								key={summary.id}
								className={cn(
									"relative group flex items-center gap-2",
									isActive &&
										"bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg",
								)}
							>
								<button
									type="button"
									onClick={() => onSelectThread(summary.id)}
									className={cn(
										"flex-1 text-left px-4 py-2.5 rounded-lg border transition-all duration-200",
										isActive
											? "bg-transparent text-white border-transparent shadow-md"
											: "bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-slate-600 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-sm",
									)}
								>
									<div className="flex items-center justify-between">
										<span className="font-medium text-sm">
											Thread {index + 1}
										</span>
										<span
											className={cn(
												"text-xs",
												isActive
													? "text-white/80"
													: "text-gray-500 dark:text-gray-400",
											)}
										>
											{summary.message_count} msg
										</span>
									</div>
									<div
										className={cn(
											"text-xs mt-0.5",
											isActive
												? "text-white/70"
												: "text-gray-400 dark:text-gray-500",
										)}
									>
										{relative}
									</div>
								</button>
								<button
									type="button"
									onClick={(e) => onDeleteThread(summary.id, e)}
									disabled={isDisabled}
									className={cn(
										"flex items-center justify-center h-8 w-8 rounded-lg transition-all duration-200 opacity-0 group-hover:opacity-100",
										isActive
											? "text-white/70 hover:text-white hover:bg-white/20"
											: "text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20",
										isDisabled && "opacity-50 cursor-not-allowed",
									)}
									title="Delete conversation thread"
									aria-label="Delete conversation thread"
								>
									<FiTrash2 className="h-4 w-4" />
								</button>
							</div>
						);
					})}
				</div>
			</div>
		);
	},
);

ConversationThreadList.displayName = "ConversationThreadList";

export default ConversationThreadList;
