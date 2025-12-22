"use client";

import type React from "react";
import { useEffect, useState } from "react";
import { deleteContent as deleteContentSdk } from "@/client";
import { Skeleton } from "@/components/common/Skeleton";
import ContentDisplay from "@/components/features/content-generation/ContentDisplay";
import { SavedContentsList } from "@/components/features/SavedContentsList";
import { LogUploadForm } from "@/components/forms/LogUploadForm";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import {
	type UnifiedProcessingStatus,
	useJobStatusQuery,
} from "@/hooks/useJobStatusQuery";
import { useSavedContentsQuery } from "@/hooks/useSavedContentsQuery";

// Local type alias for job status response
type JobStatusResponse = UnifiedProcessingStatus;

const LogsPage: React.FC = () => {
	const { isAuthenticated, isLoading: authLoading } = useAuthGuard({
		onUserDataCleared: () => {
			setJobId(null);
			setCompletedStatus(null);
			setCurrentPage(1);
		},
	});

	const [jobId, setJobId] = useState<string | null>(null);
	const [completedStatus, setCompletedStatus] =
		useState<JobStatusResponse | null>(null);
	const { status, error: jobError } = useJobStatusQuery(jobId, false, true);
	const [currentPage, setCurrentPage] = useState<number>(1);
	const contentsPerPage = 5;
	const {
		data: savedContents,
		isLoading: isLoadingContents,
		error: errorContents,
	} = useSavedContentsQuery(currentPage, contentsPerPage, "log-summary");

	const handleSubmitSuccess = (newJobId: string) => {
		setJobId(newJobId);
		setCompletedStatus(null);
	};

	useEffect(() => {
		if (status?.status === "completed") {
			setCompletedStatus(status);
			setJobId(null);
			setCurrentPage(1);
		} else if (status?.status === "failed") {
			setJobId(null);
		}
	}, [status?.status, status]);

	if (authLoading || !isAuthenticated) {
		return (
			<div className="max-w-4xl mx-auto py-8 px-4 space-y-8">
				<div className="morphio-card p-8 space-y-6">
					<Skeleton className="h-8 w-48" />
					<Skeleton className="h-4 w-64" />
					<Skeleton className="h-32 w-full" />
				</div>
				<div className="morphio-card p-8 space-y-6">
					<Skeleton className="h-8 w-48" />
					<Skeleton className="h-24 w-full" />
				</div>
			</div>
		);
	}

	const currentStatus = jobId ? status : completedStatus;

	return (
		<div className="max-w-4xl mx-auto py-8 px-4">
			<section className="morphio-card">
				<div className="px-8 py-6 border-b border-gray-200/50 dark:border-gray-700/50 bg-linear-to-r from-transparent via-blue-50/30 dark:via-blue-900/20 to-transparent">
					<h1 className="morphio-h3 font-semibold bg-clip-text text-transparent bg-linear-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400">
						Process Log File
					</h1>
					<p className="mt-2 morphio-body-sm text-gray-600 dark:text-gray-400">
						Upload your log files for analysis and processing
					</p>
				</div>
				<div className="p-8">
					<LogUploadForm
						onSubmitSuccess={handleSubmitSuccess}
						isSubmitting={!!jobId}
						processType="logs"
					/>

					{currentStatus && (
						<div className="mt-6 space-y-4">
							{jobId && (
								<div className="p-4 bg-gray-50/50 dark:bg-gray-900/50 rounded-xl border border-gray-100 dark:border-gray-800">
									<h2 className="morphio-h4 mb-2">Processing Status</h2>
									<div className="space-y-3">
										{(currentStatus.progress ?? 0) > 0 && (
											<div className="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
												<div
													className="absolute h-full bg-linear-to-r from-blue-500 to-purple-500 transition-all duration-300"
													style={{
														width: `${Math.round(currentStatus.progress ?? 0)}%`,
													}}
												/>
											</div>
										)}
										<p className="morphio-body-sm text-gray-600 dark:text-gray-300">
											Status: {currentStatus.status}
											{(currentStatus.progress ?? 0) > 0 &&
												` (${Math.round(currentStatus.progress ?? 0)}%)`}
										</p>
										{currentStatus.message && (
											<p className="morphio-caption text-gray-500 dark:text-gray-400">
												{currentStatus.message}
											</p>
										)}
									</div>
								</div>
							)}

							{currentStatus.result &&
								typeof currentStatus.result === "object" &&
								"summary" in currentStatus.result && (
									<section className="morphio-card">
										<ContentDisplay
											content={
												(currentStatus.result as Record<string, unknown>)
													.summary as string
											}
											title={
												((currentStatus.result as Record<string, unknown>)
													.title as string) || "Log Analysis"
											}
											showCopyButton={true}
											showAsCard={false}
											className="h-full"
										/>
									</section>
								)}
						</div>
					)}

					{jobError && (
						<div className="mt-4 p-4 bg-red-50/80 dark:bg-red-900/20 border border-red-100 dark:border-red-800/50 rounded-xl">
							<p className="morphio-body-sm text-red-600 dark:text-red-400">
								{jobError}
							</p>
						</div>
					)}
				</div>
			</section>

			<section className="mt-8 morphio-card">
				<div className="px-8 py-6 border-b border-gray-200/50 dark:border-gray-700/50 bg-linear-to-r from-transparent via-purple-50/30 dark:via-purple-900/20 to-transparent">
					<h2 className="morphio-h3 font-semibold bg-clip-text text-transparent bg-linear-to-r from-purple-600 to-pink-600 dark:from-purple-400 dark:to-pink-400">
						Saved Log Summaries
					</h2>
				</div>
				<div className="p-8">
					<SavedContentsList
						contents={savedContents?.items || []}
						isLoading={isLoadingContents}
						onDelete={async (id: number) => {
							await deleteContentSdk({ path: { content_id: id } });
							setCurrentPage(1);
						}}
						onRefresh={() => setCurrentPage(1)}
						currentPage={currentPage}
						onPageChange={setCurrentPage}
						totalPages={
							savedContents
								? Math.ceil(savedContents.total / contentsPerPage)
								: 1
						}
						error={errorContents}
					/>
				</div>
			</section>
		</div>
	);
};

export default LogsPage;
