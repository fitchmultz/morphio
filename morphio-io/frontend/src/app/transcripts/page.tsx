"use client";

import type React from "react";
import { useEffect, useState } from "react";
import {
	getMediaConfig,
	getMediaProcessingStatus,
	getUserProfile,
	type MediaProcessingStatusResponse,
	processMedia,
} from "@/client";
import { Skeleton } from "@/components/common/Skeleton";
import ContentDisplay from "@/components/features/content-generation/ContentDisplay";
import FileUpload from "@/components/features/content-generation/FileUpload";
import FormProgress from "@/components/features/content-generation/FormProgress";
// Import our reusable components
import UrlInput from "@/components/features/content-generation/UrlInput";
import { ContentSource, MediaType } from "@/constants/media";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import logger from "@/lib/logger";
import { notifySuccess } from "@/lib/toast";
import { detectUrlSource, guessMediaType } from "@/utils/mediaUtils";

// Polling interval for job status checks (in milliseconds)
const POLLING_INTERVAL_MS = 2000;

const TranscriptPage: React.FC = () => {
	const { isAuthenticated, isLoading: authLoading } = useAuthGuard({
		onUserDataCleared: () => {
			setInputUrl("");
			setInputFile(null);
			setIsLoading(false);
			setStatusMessage("");
			setProgress(0);
			setJobId(null);
			setTranscriptResult("");
			setError(null);
			setCurrentStatus(null);
		},
	});

	const [inputUrl, setInputUrl] = useState("");
	const [inputFile, setInputFile] = useState<File | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [statusMessage, setStatusMessage] = useState("");
	const [progress, setProgress] = useState(0);
	const [jobId, setJobId] = useState<string | null>(null);
	const [transcriptResult, setTranscriptResult] = useState<string>("");
	const [error, setError] = useState<string | null>(null);
	const [autoDetectedType, setAutoDetectedType] = useState<MediaType | null>(
		null,
	);
	const [currentStatus, setCurrentStatus] =
		useState<MediaProcessingStatusResponse | null>(null);

	// Set a default value, but we'll try to get it from the API
	const [maxUploadSize, setMaxUploadSize] = useState<number>(
		parseInt(process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE || "3221225472", 10),
	);

	// Prefetch user data
	useEffect(() => {
		if (!authLoading && isAuthenticated) {
			getUserProfile()
				.then((resp) => {
					if (resp.data?.data) {
						logger.info("Prefetched user profile on transcripts page");
					} else {
						logger.warn("Could not prefetch user profile", resp);
					}
				})
				.catch((err: unknown) => {
					logger.warn("Could not prefetch user profile in transcripts page", {
						err,
					});
				});
		}
	}, [authLoading, isAuthenticated]);

	useEffect(() => {
		// Fetch the max upload size from the backend
		const fetchMaxUploadSize = async () => {
			try {
				const { data } = await getMediaConfig();
				if (data?.status === "success" && data.data) {
					const configData = data.data as { max_upload_size?: number };
					if (configData.max_upload_size) {
						setMaxUploadSize(configData.max_upload_size);
					}
				}
			} catch (error: unknown) {
				const msg = error instanceof Error ? error.message : "Unknown error";
				logger.warn("Config unavailable, using defaults", { error: msg });
				// No user toast - silent fallback to defaults
			}
		};

		fetchMaxUploadSize();
	}, []);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setIsLoading(true);
		setTranscriptResult("");
		setError(null);
		setStatusMessage("");
		setProgress(0);

		try {
			let source: ContentSource;
			let mediaType: MediaType | undefined;

			if (inputFile) {
				source = ContentSource.UPLOAD;
				mediaType = autoDetectedType ?? guessMediaType(inputFile) ?? undefined;
			} else if (inputUrl) {
				source = detectUrlSource(inputUrl);
				// if youtube or rumble => video, if spotify => audio, else => web
				if (
					source === ContentSource.YOUTUBE ||
					source === ContentSource.RUMBLE
				) {
					mediaType = MediaType.VIDEO;
				} else if (source === ContentSource.SPOTIFY) {
					mediaType = MediaType.AUDIO;
				}
			} else {
				throw new Error("No input (URL or file) provided");
			}

			const { data, error } = await processMedia({
				body: {
					template_id: "0", // transcript-only
					model: "",
					media_type: mediaType || "video",
					input_file: inputFile,
					input_url: inputUrl || "",
				},
			});

			if (error) {
				throw new Error(error instanceof Error ? error.message : String(error));
			}
			if (data?.data?.job_id) {
				setJobId(data.data.job_id);
			} else {
				throw new Error("Failed to initiate transcript job");
			}
		} catch (err) {
			setError(err instanceof Error ? err.message : "An error occurred");
			setIsLoading(false);
		}
	};

	useEffect(() => {
		if (!jobId) return;

		let active = true;
		let timeoutId: NodeJS.Timeout | null = null;
		const controller = new AbortController();

		const pollStatus = async () => {
			if (!active) return;

			try {
				const { data, error: fetchError } = await getMediaProcessingStatus({
					path: { job_id: jobId },
					signal: controller.signal,
				});

				// Ignore if unmounted or job changed
				if (!active) return;

				if (fetchError) {
					throw new Error(
						fetchError instanceof Error
							? fetchError.message
							: String(fetchError),
					);
				}
				const statusData = data?.data;
				if (statusData) {
					setCurrentStatus(statusData);
					setProgress(statusData.progress ?? 0);
					setStatusMessage(statusData.message || "");
					if (statusData.status === "completed") {
						const result = statusData.result;
						if (result && typeof result === "object" && "content" in result) {
							setTranscriptResult(
								(result as Record<string, unknown>).content as string,
							);
							notifySuccess("Transcript retrieved successfully!");
						} else {
							setError("Transcript was empty or not found in the job result.");
						}
						setIsLoading(false);
						setJobId(null);
					} else if (statusData.status === "failed") {
						setError(statusData.error || "Transcript job failed");
						setIsLoading(false);
						setJobId(null);
					} else {
						// Still processing - schedule next poll after this one completes
						timeoutId = setTimeout(pollStatus, POLLING_INTERVAL_MS);
					}
				} else {
					throw new Error("Unexpected transcript status response");
				}
			} catch (err) {
				// Ignore abort errors and check if still active
				if (!active) return;
				if (err instanceof Error && err.name === "AbortError") return;

				setError(
					err instanceof Error ? err.message : "An error occurred polling job",
				);
				setIsLoading(false);
				setJobId(null);
			}
		};

		// Start first poll immediately
		pollStatus();

		return () => {
			active = false;
			controller.abort();
			if (timeoutId) clearTimeout(timeoutId);
		};
	}, [jobId]);

	if (authLoading || !isAuthenticated) {
		return (
			<div className="min-h-screen py-8">
				<div className="max-w-4xl mx-auto px-4 space-y-6">
					<Skeleton className="h-10 w-64" />
					<Skeleton className="h-6 w-full max-w-lg" />
					<Skeleton className="h-32 w-full" />
					<Skeleton className="h-32 w-full" />
					<Skeleton className="h-12 w-full" />
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen py-8">
			<div className="max-w-4xl mx-auto px-4">
				<h1 className="morphio-h3 font-semibold bg-clip-text text-transparent bg-linear-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 mb-6">
					Transcript Generator
				</h1>
				<p className="morphio-body mb-8">
					Retrieve a raw transcript from a YouTube link, Rumble link, Spotify
					link, or an uploaded audio/video file. Otherwise, it will scrape text
					from the given page if possible.
				</p>

				<form onSubmit={handleSubmit} className="space-y-6">
					<UrlInput
						inputUrl={inputUrl}
						setInputUrl={setInputUrl}
						setAutoDetectedType={setAutoDetectedType}
						isLoading={isLoading}
						hasFile={!!inputFile}
					/>

					<FileUpload
						inputFile={inputFile}
						setInputFile={setInputFile}
						setAutoDetectedType={setAutoDetectedType}
						isLoading={isLoading}
						hasUrl={!!inputUrl}
						maxUploadSize={maxUploadSize}
					/>

					{error && (
						<div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 rounded-xl">
							<p className="morphio-body-sm text-red-600 dark:text-red-400">
								{error}
							</p>
						</div>
					)}

					<FormProgress
						isLoading={isLoading}
						progress={progress}
						stage={currentStatus?.stage}
						statusMessage={statusMessage}
						error={error}
					/>

					<button
						type="submit"
						disabled={isLoading || (!inputUrl && !inputFile)}
						className="morphio-button w-full px-6 py-3.5 disabled:from-gray-300 disabled:to-gray-300 dark:disabled:from-gray-700 dark:disabled:to-gray-700 disabled:hover:transform-none disabled:cursor-not-allowed disabled:opacity-50"
					>
						{isLoading ? "Processing..." : "Generate Transcript"}
					</button>
				</form>

				{transcriptResult && (
					<div className="mt-10">
						<div className="morphio-card">
							<ContentDisplay
								content={transcriptResult}
								title="Generated Transcript"
								showCopyButton={true}
								showAsCard={false}
								className="h-full"
							/>
						</div>
					</div>
				)}
			</div>
		</div>
	);
};

export default TranscriptPage;
