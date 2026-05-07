"use client";

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

interface ProcessedContentPageProps {
	processType: "logs" | "splunk";
	savedContentType: "log-summary" | "splunk-config";
	resultKey: "summary" | "content";
	pageTitle: string;
	pageDescription: string;
	savedTitle: string;
	fallbackResultTitle: string;
	accentClasses: {
		headerVia: string;
		titleGradient: string;
		progressGradient: string;
		savedHeaderVia: string;
		savedTitleGradient: string;
	};
}

const getResultText = (
	status: UnifiedProcessingStatus | null,
	resultKey: ProcessedContentPageProps["resultKey"],
) => {
	const result = status?.result;
	if (!result || typeof result !== "object" || !(resultKey in result)) {
		return null;
	}
	const resultRecord = result as Record<string, unknown>;
	const value = resultRecord[resultKey];
	if (typeof value !== "string") {
		return null;
	}
	return {
		content: value,
		title: typeof resultRecord.title === "string" ? resultRecord.title : null,
	};
};

export function ProcessedContentPage({
	processType,
	savedContentType,
	resultKey,
	pageTitle,
	pageDescription,
	savedTitle,
	fallbackResultTitle,
	accentClasses,
}: ProcessedContentPageProps) {
	const [jobId, setJobId] = useState<string | null>(null);
	const [completedStatus, setCompletedStatus] =
		useState<UnifiedProcessingStatus | null>(null);
	const [currentPage, setCurrentPage] = useState<number>(1);

	const { isAuthenticated, isLoading: authLoading } = useAuthGuard({
		onUserDataCleared: () => {
			setJobId(null);
			setCompletedStatus(null);
			setCurrentPage(1);
		},
	});
	const { status, error: jobError } = useJobStatusQuery(jobId, false, true);
	const contentsPerPage = 5;
	const {
		data: savedContents,
		isLoading: isLoadingContents,
		error: errorContents,
	} = useSavedContentsQuery(currentPage, contentsPerPage, savedContentType);

	useEffect(() => {
		if (status?.status === "completed") {
			setCompletedStatus(status);
			setJobId(null);
			setCurrentPage(1);
		} else if (status?.status === "failed") {
			setJobId(null);
		}
	}, [status]);

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
	const result = getResultText(currentStatus, resultKey);

	return (
		<div className="max-w-4xl mx-auto py-8 px-4">
			<section className="morphio-card">
				<div
					className={`px-8 py-6 border-b border-gray-200/50 dark:border-gray-700/50 bg-linear-to-r from-transparent ${accentClasses.headerVia} to-transparent`}
				>
					<h1
						className={`morphio-h3 font-semibold bg-clip-text text-transparent bg-linear-to-r ${accentClasses.titleGradient}`}
					>
						{pageTitle}
					</h1>
					<p className="mt-2 morphio-body-sm text-gray-600 dark:text-gray-400">
						{pageDescription}
					</p>
				</div>
				<div className="p-8">
					<LogUploadForm
						onSubmitSuccess={(newJobId) => {
							setJobId(newJobId);
							setCompletedStatus(null);
						}}
						isSubmitting={!!jobId}
						processType={processType}
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
													className={`absolute h-full bg-linear-to-r ${accentClasses.progressGradient} transition-all duration-300`}
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

							{result && (
								<section className="morphio-card">
									<ContentDisplay
										content={result.content}
										title={result.title || fallbackResultTitle}
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
				<div
					className={`px-8 py-6 border-b border-gray-200/50 dark:border-gray-700/50 bg-linear-to-r from-transparent ${accentClasses.savedHeaderVia} to-transparent`}
				>
					<h2
						className={`morphio-h3 font-semibold bg-clip-text text-transparent bg-linear-to-r ${accentClasses.savedTitleGradient}`}
					>
						{savedTitle}
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
}
