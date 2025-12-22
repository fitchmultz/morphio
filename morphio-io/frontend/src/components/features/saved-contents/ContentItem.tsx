import type React from "react";
import {
	FaChevronDown,
	FaChevronUp,
	FaCopy,
	FaPencilAlt,
	FaTrash,
} from "react-icons/fa";
import type { ContentOut } from "@/client/types.gen";

interface ContentItemProps {
	content: ContentOut;
	isExpanded: boolean;
	onToggle: () => void;
	onCopyContent: () => void;
	onEditTitle: () => void;
	onDeleteClick: () => void;
	formatCreatedAt: (dateString: string) => string;
}

const ContentItem: React.FC<ContentItemProps> = ({
	content,
	isExpanded,
	onToggle,
	onCopyContent,
	onEditTitle,
	onDeleteClick,
	formatCreatedAt,
}) => {
	return (
		<div className="w-full morphio-card mb-4" data-content-id={content.id}>
			<div className="p-4 flex flex-col lg:flex-row gap-2 lg:gap-4 items-start lg:items-center justify-between">
				<div className="flex-1 space-y-1 min-w-0">
					<h3 className="morphio-h4 truncate">{content.title}</h3>
					<div className="flex flex-wrap gap-2 morphio-body-sm text-gray-500 dark:text-gray-400">
						<span>{formatCreatedAt(content.created_at)}</span>
						{content.tags && content.tags.length > 0 && (
							<>
								<span>•</span>
								<div className="flex flex-wrap gap-1">
									{content.tags.map((tag) => (
										<span
											key={tag}
											className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-300"
										>
											{tag}
										</span>
									))}
								</div>
							</>
						)}
					</div>
				</div>

				<div className="flex flex-wrap gap-2 text-sm">
					<button
						type="button"
						onClick={onEditTitle}
						className="morphio-icon-button inline-flex items-center px-3 py-1.5 border border-gray-200 dark:border-gray-700"
						title="Edit title"
					>
						<FaPencilAlt className="mr-1.5" />
						Edit
					</button>
					<button
						type="button"
						onClick={onCopyContent}
						className="morphio-icon-button inline-flex items-center px-3 py-1.5 border border-gray-200 dark:border-gray-700"
						title="Copy to clipboard"
					>
						<FaCopy className="mr-1.5" />
						Copy
					</button>
					<button
						type="button"
						onClick={onDeleteClick}
						className="morphio-icon-button inline-flex items-center px-3 py-1.5 border border-red-200 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
						title="Delete"
					>
						<FaTrash className="mr-1.5" />
						Delete
					</button>
					<button
						type="button"
						onClick={onToggle}
						className="morphio-icon-button inline-flex items-center px-3 py-1.5 border border-gray-200 dark:border-gray-700"
						title={isExpanded ? "Collapse" : "Expand"}
					>
						{isExpanded ? (
							<>
								<FaChevronUp className="mr-1.5" />
								Collapse
							</>
						) : (
							<>
								<FaChevronDown className="mr-1.5" />
								View
							</>
						)}
					</button>
				</div>
			</div>
		</div>
	);
};

export default ContentItem;
