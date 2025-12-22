"use client";

import type React from "react";
import { memo } from "react";
import { FiSend } from "react-icons/fi";

interface ChatInputFormProps {
	value: string;
	onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
	onSubmit: (e: React.FormEvent) => void;
	isDisabled: boolean;
	contentId: number | null;
	maxLength?: number;
	isNearLimit?: boolean;
	charactersRemaining?: number;
}

const ChatInputForm: React.FC<ChatInputFormProps> = memo(
	({
		value,
		onChange,
		onSubmit,
		isDisabled,
		contentId,
		maxLength = 5000,
		isNearLimit = false,
		charactersRemaining = 5000,
	}) => {
		return (
			<form
				onSubmit={onSubmit}
				className="border-t border-slate-200/60 px-6 py-5 dark:border-slate-700/60 bg-white dark:bg-gray-800"
			>
				<label
					htmlFor="conversation-input"
					className="morphio-overline mb-2 block"
				>
					Ask Morphio to refine
				</label>
				<div className="relative">
					<textarea
						id="conversation-input"
						value={value}
						onChange={onChange}
						disabled={isDisabled || !contentId}
						rows={3}
						maxLength={maxLength}
						placeholder={
							contentId
								? "Describe what should change..."
								: "Save content to enable chat"
						}
						className="w-full px-4 py-3.5 pr-12 bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700/50 rounded-xl focus:ring-2 focus:ring-blue-500/40 dark:focus:ring-blue-400/50 focus:border-transparent placeholder-gray-400 dark:placeholder-gray-500 text-gray-900 dark:text-gray-200 shadow-xs hover:bg-white dark:hover:bg-gray-900/60 transition-all duration-200 resize-none"
					/>
					<button
						type="submit"
						disabled={isDisabled || !contentId || !value.trim()}
						className="absolute bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-md transition-all duration-200 hover:from-blue-600 hover:to-purple-600 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-md"
						title="Send message"
					>
						<FiSend className="h-4 w-4" />
					</button>
				</div>
				<div className="mt-2 flex items-center justify-between">
					<span className="morphio-caption text-xs text-slate-400 dark:text-slate-500">
						{isNearLimit && (
							<span className="text-amber-600 dark:text-amber-400">
								{charactersRemaining} characters remaining ·{" "}
							</span>
						)}
						Reference specific sections or tones
					</span>
				</div>
			</form>
		);
	},
);

ChatInputForm.displayName = "ChatInputForm";

export default ChatInputForm;
