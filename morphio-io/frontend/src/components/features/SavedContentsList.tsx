"use client";

import { formatDistanceToNow, isValid, parseISO } from "date-fns";
import { toZonedTime } from "date-fns-tz";
import React, { type FC, useCallback, useState } from "react";
import {
	type ContentOut,
	updateContentTitle as updateContentTitleSdk,
} from "@/client";
import { Skeleton } from "@/components/common/Skeleton";
import ContentWithChat from "@/components/features/content-generation/ContentWithChat";
import logger from "@/lib/logger";
import { notifyError, notifySuccess } from "@/lib/toast";

// Local type alias
type Content = ContentOut;

// Import sub-components
import ContentItem from "./saved-contents/ContentItem";
import ContentPagination from "./saved-contents/ContentPagination";
import ContentSearchBar from "./saved-contents/ContentSearchBar";
import DeleteConfirmationModal from "./saved-contents/DeleteConfirmationModal";
import TitleEditor from "./saved-contents/TitleEditor";

interface SavedContentsListProps {
	contents: Content[];
	isLoading: boolean;
	onDelete: (id: number) => Promise<void>;
	onRefresh: () => void;
	currentPage: number;
	onPageChange: (page: number) => void;
	totalPages?: number;
	error?: string | null;
}

const formatCreatedAt = (dateString: string): string => {
	try {
		const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

		let adjustedDateString = dateString;
		// Append 'Z' if no timezone info is present
		if (!/([Z]|[+-]\d{2}:\d{2})$/.test(dateString)) {
			adjustedDateString = `${dateString}Z`;
		}
		const date = parseISO(adjustedDateString);
		if (!isValid(date)) {
			logger.error("Invalid date received from API", { dateString });
			return "Invalid date";
		}

		const zonedDate = toZonedTime(date, userTimeZone);
		return formatDistanceToNow(zonedDate, { addSuffix: true });
	} catch (error) {
		logger.error("Error formatting date", {
			dateString,
			error: error instanceof Error ? error.message : String(error),
		});
		return "Unknown date";
	}
};

export const SavedContentsList: FC<SavedContentsListProps> = React.memo(
	({
		contents,
		isLoading,
		onDelete,
		onRefresh,
		currentPage,
		onPageChange,
		totalPages,
		error,
	}) => {
		const [expandedContent, setExpandedContent] = useState<number | null>(null);
		const [searchTerm, setSearchTerm] = useState("");
		const [editingTitleId, setEditingTitleId] = useState<number | null>(null);
		const [contentToDelete, setContentToDelete] = useState<number | null>(null);
		const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
		const [isDeleting, setIsDeleting] = useState(false);

		const toggleContent = useCallback((id: number) => {
			setExpandedContent((current) => (current === id ? null : id));
		}, []);

		const copyToClipboard = useCallback(async (text: string) => {
			try {
				await navigator.clipboard.writeText(text);
				notifySuccess("Content copied to clipboard!");
			} catch (err) {
				logger.error("Failed to copy content", {
					error: err instanceof Error ? err.message : String(err),
				});
				notifyError("Failed to copy content.");
			}
		}, []);

		const handleDeleteClick = useCallback((id: number) => {
			setContentToDelete(id);
			setIsDeleteModalOpen(true);
		}, []);

		const handleDeleteConfirm = useCallback(async () => {
			if (contentToDelete === null) return;

			setIsDeleting(true);
			try {
				await onDelete(contentToDelete);
				setIsDeleteModalOpen(false);
				setContentToDelete(null);
			} catch (error) {
				logger.error("Error in SavedContentsList delete handler", {
					contentId: contentToDelete,
					error: error instanceof Error ? error.message : String(error),
				});
				// Error notification is handled by the parent component
			} finally {
				setIsDeleting(false);
			}
		}, [contentToDelete, onDelete]);

		const handleEditTitle = useCallback((id: number) => {
			setEditingTitleId(id);
		}, []);

		const saveTitle = useCallback(
			async (id: number, newTitle: string) => {
				try {
					const { data, error } = await updateContentTitleSdk({
						path: { content_id: id },
						body: { title: newTitle },
					});
					if (error) {
						throw new Error(
							error instanceof Error ? error.message : String(error),
						);
					}
					if (data?.status === "success") {
						notifySuccess("Title updated successfully");
						setEditingTitleId(null);
						onRefresh();
					} else {
						throw new Error(data?.message || "Failed to update title");
					}
				} catch (error) {
					logger.error("Error updating content title", {
						contentId: id,
						error: error instanceof Error ? error.message : String(error),
					});
					notifyError(
						error instanceof Error
							? error.message
							: "An unexpected error occurred",
					);
				}
			},
			[onRefresh],
		);

		const cancelEditTitle = useCallback(() => {
			setEditingTitleId(null);
		}, []);

		const handleSearchChange = useCallback((term: string) => {
			setSearchTerm(term);
		}, []);

		const filteredContents = contents.filter((content) =>
			content.title.toLowerCase().includes(searchTerm.toLowerCase()),
		);

		if (isLoading) {
			return (
				<div className="space-y-4">
					<Skeleton variant="text" className="w-full h-10" />
					<div className="space-y-6">
						<Skeleton variant="card" className="h-32" />
						<Skeleton variant="card" className="h-32" />
						<Skeleton variant="card" className="h-32" />
					</div>
				</div>
			);
		}

		return (
			<div className="space-y-6">
				<ContentSearchBar
					searchTerm={searchTerm}
					onSearchChange={handleSearchChange}
				/>

				{error ? (
					<div className="morphio-card p-4 bg-red-50/20 dark:bg-red-900/10 border border-red-100/50 dark:border-red-800/30 rounded-xl">
						<p className="morphio-body-sm text-center text-red-600 dark:text-red-400">
							{error}
						</p>
					</div>
				) : filteredContents.length === 0 ? (
					<div className="text-center py-12 space-y-2">
						<div className="morphio-body-lg text-gray-400 dark:text-gray-500">
							{searchTerm
								? `No content matching "${searchTerm}"`
								: "No saved content yet"}
						</div>
						{searchTerm && (
							<button
								type="button"
								onClick={() => setSearchTerm("")}
								className="morphio-link text-sm"
							>
								Clear search
							</button>
						)}
						{!searchTerm && contents.length === 0 && (
							<p className="morphio-body-sm text-gray-400 dark:text-gray-500">
								Generate content to see it here
							</p>
						)}
					</div>
				) : (
					<div className="space-y-4">
						{filteredContents.map((content) => (
							<div key={content.id}>
								<ContentItem
									content={content}
									isExpanded={expandedContent === content.id}
									onToggle={() => toggleContent(content.id)}
									onCopyContent={() => copyToClipboard(content.content)}
									onEditTitle={() => handleEditTitle(content.id)}
									onDeleteClick={() => handleDeleteClick(content.id)}
									formatCreatedAt={formatCreatedAt}
								/>

								{expandedContent === content.id && (
									<div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700">
										<ContentWithChat
											content={content.content}
											contentId={content.id}
											title={content.title}
											templateName={content.template?.name || null}
											showContentAsCard={false}
											onContentUpdate={() => onRefresh()}
											onRefreshRequested={onRefresh}
											className="py-2"
										/>
									</div>
								)}

								{editingTitleId === content.id && (
									<TitleEditor
										contentId={content.id}
										currentTitle={content.title}
										onSave={saveTitle}
										onCancel={cancelEditTitle}
									/>
								)}
							</div>
						))}
					</div>
				)}

				<ContentPagination
					currentPage={currentPage}
					totalPages={totalPages}
					onPageChange={onPageChange}
				/>

				{contentToDelete !== null && (
					<DeleteConfirmationModal
						isOpen={isDeleteModalOpen}
						contentTitle={
							contents.find((c) => c.id === contentToDelete)?.title ||
							"this content"
						}
						onClose={() => {
							setIsDeleteModalOpen(false);
							setContentToDelete(null);
						}}
						onConfirm={handleDeleteConfirm}
						isDeleting={isDeleting}
					/>
				)}
			</div>
		);
	},
);

SavedContentsList.displayName = "SavedContentsList";
