"use client";

import { FaCopy, FaPencilAlt, FaStar, FaTrash } from "react-icons/fa";
import type { TemplateOut } from "@/client";

export interface TemplateListItemProps {
	template: TemplateOut;
	variant: "custom" | "default";
	isPinned: boolean;
	onEdit?: (templateId: number) => void;
	onClone?: (template: TemplateOut) => void;
	onDelete?: (templateId: number) => void;
	onTogglePin: (templateId: number) => void;
}

export function TemplateListItem({
	template,
	variant,
	isPinned,
	onEdit,
	onClone,
	onDelete,
	onTogglePin,
}: TemplateListItemProps) {
	return (
		<div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 group hover:shadow-md transition-all duration-200">
			<div className="flex-1 min-w-0">
				<h3 className="morphio-h4 truncate">{template.name}</h3>
				<p className="mt-1 morphio-body-sm text-gray-500 dark:text-gray-400 line-clamp-2">
					{variant === "custom" ? "Custom Template" : "Default Template"}
				</p>
			</div>
			<div className="flex items-center gap-2 ml-4">
				{variant === "custom" && onEdit && (
					<button
						type="button"
						onClick={() => onEdit(template.id)}
						className="p-2 text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200"
						title="Edit template"
					>
						<FaPencilAlt className="h-4 w-4" />
					</button>
				)}
				{variant === "default" && onClone && (
					<button
						type="button"
						onClick={() => onClone(template)}
						className="p-2 text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200"
						title="Clone template"
					>
						<FaCopy className="h-4 w-4" />
					</button>
				)}
				<button
					type="button"
					onClick={() => onTogglePin(template.id)}
					className="p-2 text-yellow-500 hover:text-yellow-600 dark:text-yellow-400 dark:hover:text-yellow-300 hover:bg-yellow-50 dark:hover:bg-yellow-900/30 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200"
					title="Pin/Unpin template"
				>
					<FaStar
						className={`h-4 w-4 ${
							isPinned ? "text-yellow-500" : "text-yellow-500 opacity-40"
						}`}
					/>
				</button>
				{variant === "custom" && onDelete && (
					<button
						type="button"
						onClick={() => onDelete(template.id)}
						className="p-2 text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200"
						title="Delete template"
					>
						<FaTrash className="h-4 w-4" />
					</button>
				)}
			</div>
		</div>
	);
}
