"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { deleteContent as deleteContentSdk, processMedia } from "@/client";
import Modal from "@/components/common/Modal";
import { Skeleton } from "@/components/common/Skeleton";
import { ContentGenerationForm } from "@/components/features/ContentGenerationForm";
import ContentWithChat from "@/components/features/content-generation/ContentWithChat";
import { SavedContentsList } from "@/components/features/SavedContentsList";
import { ManageTemplatesModal } from "@/components/features/templates";
import { CreateTemplateForm } from "@/components/forms/CreateTemplateForm";
import { EditTemplateForm } from "@/components/forms/EditTemplateForm";
import { ContentSource } from "@/constants/media";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { useJobStatusQuery } from "@/hooks/useJobStatusQuery";
import { useSavedContentsQuery } from "@/hooks/useSavedContentsQuery";
import { useTemplateManagement } from "@/hooks/useTemplateManagement";
import { useTemplatesQuery } from "@/hooks/useTemplatesQuery";
import { notifyError, notifySuccess } from "@/lib/toast";

// Unified processing input
interface UnifiedProcessingInput {
	template_id: number | string;
	model: string;
	source: ContentSource;
	file: File | null;
	url: string;
	media_type?: string;
	enable_diarization?: boolean;
	min_speakers?: number | null;
	max_speakers?: number | null;
}

function Dashboard() {
	const { isAuthenticated, isLoading: authLoading } = useAuthGuard({
		onUserDataCleared: () => {
			setCurrentPage(1);
			setShowCreateTemplateModal(false);
			setShowManageTemplatesModal(false);
			setEditingTemplateId(null);
			setFormResetTrigger((prev) => prev + 1);
			setOutputContent("");
			setJobId(null);
		},
	});

	const [currentPage, setCurrentPage] = useState<number>(1);
	const contentsPerPage = 5;
	const {
		data: savedContents,
		isLoading: isLoadingContents,
		error: errorContents,
		refetch: refetchSavedContents,
	} = useSavedContentsQuery(currentPage, contentsPerPage);
	const {
		data: templates,
		error: errorTemplates,
		refetch: refetchTemplates,
	} = useTemplatesQuery();

	const {
		pinnedDefault,
		pinnedCustom,
		cloneDefaultTemplate,
		deleteTemplateById,
		togglePin,
		isPinned,
	} = useTemplateManagement({ templates, refetch: refetchTemplates });

	const [jobId, setJobId] = useState<string | null>(null);
	const [isWebProcessing, setIsWebProcessing] = useState<boolean>(false);
	const { status, error: jobError } = useJobStatusQuery(jobId, isWebProcessing);
	const [outputContent, setOutputContent] = useState<string>("");
	const [outputTitle, setOutputTitle] = useState<string>("");
	const [outputContentId, setOutputContentId] = useState<number | null>(null);
	const [showCreateTemplateModal, setShowCreateTemplateModal] = useState(false);
	const [showManageTemplatesModal, setShowManageTemplatesModal] =
		useState(false);
	const [editingTemplateId, setEditingTemplateId] = useState<number | null>(
		null,
	);
	const [formResetTrigger, setFormResetTrigger] = useState(0);
	const outputRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (outputContent && outputRef.current) {
			outputRef.current.scrollIntoView({ behavior: "smooth" });
		}
	}, [outputContent]);

	useEffect(() => {
		if (status?.status === "completed" && status.result) {
			const result = status.result as Record<string, unknown>;
			if (result.content) {
				setOutputContent(result.content as string);
			}
			setOutputContentId((result.content_id as number) ?? null);
			setOutputTitle((result.title as string) || "Generated Content");
			setFormResetTrigger((prev) => prev + 1);
			notifySuccess("Content generated successfully");
			setJobId(null);
		} else if (status?.status === "failed" && "error" in status) {
			notifyError((status.error as string) || "Processing failed");
			setJobId(null);
		}
	}, [status]);

	const handleSubmit = useCallback(async (input: UnifiedProcessingInput) => {
		setIsWebProcessing(input.source === ContentSource.WEB);
		try {
			const { data, error } = await processMedia({
				body: {
					template_id: String(input.template_id),
					model: input.model,
					media_type: input.media_type || "video",
					input_file: input.file,
					input_url: input.url,
					enable_diarization: input.enable_diarization,
					min_speakers: input.min_speakers,
					max_speakers: input.max_speakers,
				},
			});
			if (error) {
				throw new Error(error instanceof Error ? error.message : String(error));
			}
			if (data?.job_id) {
				setJobId(data.job_id);
			} else {
				throw new Error("No job ID received from the server");
			}
		} catch (err) {
			notifyError(err instanceof Error ? err.message : "An error occurred");
		}
	}, []);

	const handleDeleteContent = useCallback(async (contentId: number) => {
		try {
			const { error } = await deleteContentSdk({
				path: { content_id: contentId },
			});
			if (error) {
				throw new Error(error instanceof Error ? error.message : String(error));
			}
			notifySuccess("Content deleted successfully");
			setCurrentPage(1);
		} catch {
			notifyError("Failed to delete content");
		}
	}, []);

	const handleEditTemplate = useCallback((templateId: number) => {
		setEditingTemplateId(templateId);
		setShowManageTemplatesModal(false);
	}, []);

	const handleRefresh = useCallback(() => {
		setCurrentPage(1);
		void refetchSavedContents();
	}, [refetchSavedContents]);

	const editingTemplate = useMemo(() => {
		if (editingTemplateId === null) return undefined;
		return (
			pinnedCustom.find((t) => t.id === editingTemplateId) ||
			pinnedDefault.find((t) => t.id === editingTemplateId)
		);
	}, [editingTemplateId, pinnedCustom, pinnedDefault]);

	if (authLoading || !isAuthenticated) {
		return (
			<div className="min-h-screen bg-linear-to-br from-gray-50 via-blue-50 to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
				<div className="max-w-7xl mx-auto py-12 px-4">
					<Skeleton />
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen">
			<div className="max-w-7xl mx-auto space-y-8">
				<section className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-2xl shadow-xl rounded-2xl border border-gray-200/50 dark:border-gray-700/50 overflow-hidden transform transition-all duration-300 hover:shadow-2xl hover:-translate-y-1">
					<div className="px-8 py-6 border-b border-gray-200/50 dark:border-gray-700/50 bg-linear-to-r from-transparent via-blue-50/30 dark:via-blue-900/20 to-transparent">
						<h2 className="text-3xl font-bold bg-clip-text text-transparent bg-linear-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400">
							Generate Content
						</h2>
					</div>
					<div className="p-8">
						<ContentGenerationForm
							onSubmit={handleSubmit}
							templates={{
								default: pinnedDefault || [],
								custom: pinnedCustom || [],
							}}
							isLoading={jobId !== null}
							error={jobError || errorContents || errorTemplates}
							progress={status?.progress}
							statusMessage={status?.message ?? undefined}
							resetFormTrigger={formResetTrigger}
						/>
					</div>
				</section>

				{outputContent && (
					<section className="morphio-card">
						<ContentWithChat
							content={outputContent}
							contentId={outputContentId}
							title={outputTitle}
							onContentUpdate={(updatedContent) => {
								setOutputContent(updatedContent);
								void refetchSavedContents();
							}}
							onRefreshRequested={() => void refetchSavedContents()}
						/>
					</section>
				)}

				<section className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-2xl shadow-xl rounded-2xl border border-gray-200/50 dark:border-gray-700/50 overflow-hidden transform transition-all duration-300 hover:shadow-2xl">
					<div className="px-8 py-6 border-b border-gray-200/50 dark:border-gray-700/50 bg-linear-to-r from-transparent via-purple-50/30 dark:via-purple-900/20 to-transparent">
						<div className="flex justify-between items-center">
							<h2 className="text-3xl font-bold bg-clip-text text-transparent bg-linear-to-r from-purple-600 to-pink-600 dark:from-purple-400 dark:to-pink-400">
								Saved Content
							</h2>
							<div className="flex items-center gap-4">
								<button
									type="button"
									onClick={() => setShowManageTemplatesModal(true)}
									className="morphio-button"
								>
									Edit Templates
								</button>
								<button
									type="button"
									onClick={() => setShowCreateTemplateModal(true)}
									className="morphio-button"
								>
									Create Template
								</button>
							</div>
						</div>
					</div>
					<div className="p-8">
						<SavedContentsList
							contents={savedContents?.items || []}
							isLoading={isLoadingContents}
							onDelete={handleDeleteContent}
							onRefresh={handleRefresh}
							currentPage={currentPage}
							onPageChange={setCurrentPage}
							totalPages={
								savedContents
									? Math.ceil(savedContents.total / contentsPerPage)
									: 1
							}
						/>
					</div>
				</section>

				<Modal
					isOpen={showCreateTemplateModal}
					onClose={() => setShowCreateTemplateModal(false)}
					title="Create Template"
					size="lg"
				>
					<CreateTemplateForm
						onSuccess={() => {
							setShowCreateTemplateModal(false);
							refetchTemplates();
						}}
					/>
				</Modal>

				<ManageTemplatesModal
					isOpen={showManageTemplatesModal}
					onClose={() => setShowManageTemplatesModal(false)}
					customTemplates={pinnedCustom}
					defaultTemplates={pinnedDefault}
					onEditTemplate={handleEditTemplate}
					onCloneTemplate={cloneDefaultTemplate}
					onDeleteTemplate={deleteTemplateById}
					onTogglePin={togglePin}
					isPinned={isPinned}
				/>

				<Modal
					isOpen={editingTemplateId !== null}
					onClose={() => setEditingTemplateId(null)}
					title="Edit Template"
					size="lg"
				>
					{editingTemplate && (
						<EditTemplateForm
							template={editingTemplate}
							onSuccess={() => {
								setEditingTemplateId(null);
								notifySuccess("Template updated successfully");
								refetchTemplates();
							}}
						/>
					)}
				</Modal>
			</div>
		</div>
	);
}

export default Dashboard;
