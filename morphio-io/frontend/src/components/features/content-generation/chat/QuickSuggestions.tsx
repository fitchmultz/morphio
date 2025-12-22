"use client";

import type React from "react";
import { memo } from "react";
import { FaMagic } from "react-icons/fa";

interface QuickSuggestionsProps {
	suggestions: string[];
	onSuggestionClick: (suggestion: string) => void;
	isDisabled: boolean;
}

const QuickSuggestions: React.FC<QuickSuggestionsProps> = memo(
	({ suggestions, onSuggestionClick, isDisabled }) => {
		if (suggestions.length === 0) {
			return null;
		}

		return (
			<div className="border-t border-slate-200/60 px-6 py-4 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30">
				<p className="morphio-overline mb-3 flex items-center gap-2">
					<FaMagic className="h-3.5 w-3.5" />
					Quick Suggestions
				</p>
				<div className="flex flex-wrap gap-2">
					{suggestions.map((suggestion) => (
						<button
							key={suggestion}
							type="button"
							onClick={() => onSuggestionClick(suggestion)}
							disabled={isDisabled}
							className="group rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-all duration-200 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm disabled:opacity-50 disabled:cursor-not-allowed dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300 dark:hover:border-blue-600 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
						>
							{suggestion}
						</button>
					))}
				</div>
			</div>
		);
	},
);

QuickSuggestions.displayName = "QuickSuggestions";

export default QuickSuggestions;
