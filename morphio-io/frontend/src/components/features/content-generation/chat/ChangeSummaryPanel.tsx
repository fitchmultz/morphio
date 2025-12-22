"use client";

import type React from "react";
import { memo } from "react";
import { FaMagic } from "react-icons/fa";

interface ChangeSummaryPanelProps {
	changeSummary: string[];
	notes: string | null;
}

const ChangeSummaryPanel: React.FC<ChangeSummaryPanelProps> = memo(
	({ changeSummary, notes }) => {
		if (changeSummary.length === 0) {
			return null;
		}

		return (
			<div className="bg-gradient-to-r from-blue-50/90 via-purple-50/80 to-pink-50/80 px-6 py-4 dark:from-slate-800/80 dark:via-slate-800/40 dark:to-slate-800/80 border-b border-blue-100/50 dark:border-slate-700/50">
				<div className="flex items-center gap-2 mb-2">
					<FaMagic className="h-4 w-4 text-purple-500" />
					<h4 className="morphio-h5 text-slate-700 dark:text-slate-200">
						Latest Changes
					</h4>
				</div>
				<ul className="space-y-1.5 text-sm text-slate-700 dark:text-slate-200">
					{changeSummary.map((item) => (
						<li key={item} className="flex items-start gap-2">
							<span className="text-purple-500 mt-1">•</span>
							<span>{item}</span>
						</li>
					))}
				</ul>
				{notes && (
					<div className="mt-3 pt-3 border-t border-blue-200/50 dark:border-slate-600/50">
						<p className="morphio-body-sm text-slate-600 dark:text-slate-300 italic">
							{notes}
						</p>
					</div>
				)}
			</div>
		);
	},
);

ChangeSummaryPanel.displayName = "ChangeSummaryPanel";

export default ChangeSummaryPanel;
