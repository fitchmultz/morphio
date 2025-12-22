import type React from "react";
import { type ChangeEvent, useEffect, useRef, useState } from "react";
import { FaCheckCircle, FaUpload } from "react-icons/fa";
import { getMediaConfig } from "@/client/sdk.gen";
import { MediaType } from "@/constants/media";
import logger from "@/lib/logger";
import { notifyError } from "@/lib/toast";
import {
	SUPPORTED_AUDIO_FORMATS,
	SUPPORTED_VIDEO_FORMATS,
} from "@/utils/constants";
import {
	detectFileType,
	generateAcceptAttribute,
	guessMediaType,
} from "@/utils/mediaUtils";

// Default MIME types to use if the configuration isn't available yet
const DEFAULT_ALLOWED_MIME_TYPES = [
	...SUPPORTED_VIDEO_FORMATS,
	...SUPPORTED_AUDIO_FORMATS,
];

const formatFileSizeError = (actual: number, max: number): string => {
	const actualMB = Math.round(actual / (1024 * 1024));
	const maxMB = Math.round(max / (1024 * 1024));
	return `File size (${actualMB}MB) exceeds the maximum allowed size (${maxMB}MB).`;
};

interface FileUploadProps {
	inputFile: File | null;
	setInputFile: (file: File | null) => void;
	setAutoDetectedType: (type: MediaType | null) => void;
	isLoading: boolean;
	hasUrl: boolean;
	maxUploadSize: number;
	acceptedTypes?: string;
	helpText?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({
	inputFile,
	setInputFile,
	setAutoDetectedType,
	isLoading,
	hasUrl,
	maxUploadSize: propMaxUploadSize,
	acceptedTypes,
	helpText,
}) => {
	const fileInputRef = useRef<HTMLInputElement>(null);
	const [videoExtensions, setVideoExtensions] = useState<string[]>([]);
	const [audioExtensions, setAudioExtensions] = useState<string[]>([]);
	const [maxUploadSize, setMaxUploadSize] = useState<number>(propMaxUploadSize);

	// Clear the file input when inputFile is reset to null by parent
	useEffect(() => {
		if (!inputFile && fileInputRef.current) {
			fileInputRef.current.value = "";
		}
	}, [inputFile]);

	useEffect(() => {
		if (acceptedTypes) return; // Don't fetch if acceptedTypes is provided

		let cancelled = false;

		const fetchAllowedExtensions = async () => {
			try {
				const { data } = await getMediaConfig();
				if (cancelled) return;

				if (data?.status === "success" && data.data) {
					const configData = data.data as Record<string, unknown>;
					setVideoExtensions((configData.video_extensions as string[]) || []);
					setAudioExtensions((configData.audio_extensions as string[]) || []);

					// Use the server-provided max upload size if available
					if (configData.max_upload_size) {
						setMaxUploadSize(configData.max_upload_size as number);
					}
				}
			} catch (error: unknown) {
				if (cancelled) return;
				const msg = error instanceof Error ? error.message : "Unknown error";
				logger.warn("Media config unavailable, using defaults", { error: msg });
				// No user toast - silent fallback to defaults
			}
		};

		fetchAllowedExtensions();

		return () => {
			cancelled = true;
		};
	}, [acceptedTypes]);

	const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
		const files = e.target.files;
		if (!files || files.length === 0) {
			setInputFile(null);
			setAutoDetectedType(null);
			return;
		}

		const selectedFile = files[0];
		if (selectedFile.size > maxUploadSize) {
			notifyError(formatFileSizeError(selectedFile.size, maxUploadSize));
			e.target.value = "";
			return;
		}

		const fileType = detectFileType(selectedFile);
		if (
			fileType === "unknown" &&
			(acceptedTypes === undefined || acceptedTypes === "video/*,audio/*")
		) {
			// If MIME type detection failed, try extension-based detection
			const mediaType = guessMediaType(
				selectedFile,
				videoExtensions,
				audioExtensions,
			);
			if (mediaType === MediaType.VIDEO) {
				setInputFile(selectedFile);
				setAutoDetectedType(MediaType.VIDEO);
				return;
			} else if (mediaType === MediaType.AUDIO) {
				setInputFile(selectedFile);
				setAutoDetectedType(MediaType.AUDIO);
				return;
			}

			notifyError(
				"Unsupported file type. Please upload a video or audio file in one of the supported formats.",
			);
			e.target.value = "";
			return;
		}

		setInputFile(selectedFile);
		if (fileType === "video") {
			setAutoDetectedType(MediaType.VIDEO);
		} else if (fileType === "audio") {
			setAutoDetectedType(MediaType.AUDIO);
		} else {
			setAutoDetectedType(null);
		}
	};

	const handleDrop = (e: React.DragEvent<HTMLElement>) => {
		e.preventDefault();

		if (isLoading || hasUrl) return;

		const file = e.dataTransfer.files?.[0];
		if (!file) return;

		if (file.size > maxUploadSize) {
			notifyError(formatFileSizeError(file.size, maxUploadSize));
			return;
		}

		const fileType = detectFileType(file);
		if (
			fileType === "unknown" &&
			(acceptedTypes === undefined || acceptedTypes === "video/*,audio/*")
		) {
			// If MIME type detection failed, try extension-based detection
			const mediaType = guessMediaType(file, videoExtensions, audioExtensions);
			if (mediaType === MediaType.VIDEO) {
				setInputFile(file);
				setAutoDetectedType(MediaType.VIDEO);
				return;
			} else if (mediaType === MediaType.AUDIO) {
				setInputFile(file);
				setAutoDetectedType(MediaType.AUDIO);
				return;
			}

			notifyError(
				"Unsupported file type. Please upload a video or audio file in one of the supported formats.",
			);
			return;
		}

		setInputFile(file);
		if (fileType === "video") {
			setAutoDetectedType(MediaType.VIDEO);
		} else if (fileType === "audio") {
			setAutoDetectedType(MediaType.AUDIO);
		} else {
			setAutoDetectedType(null);
		}
	};

	const getHelpText = () => {
		if (helpText) {
			return helpText;
		}

		return (
			<>
				Maximum file size: {Math.round(maxUploadSize / (1024 * 1024 * 1024))} GB
				<br />
				{videoExtensions.length > 0 && (
					<>
						Supported Video:{" "}
						{videoExtensions.map((ext) => ext.toUpperCase()).join(", ")}
						<br />
					</>
				)}
				{audioExtensions.length > 0 && (
					<>
						Supported Audio:{" "}
						{audioExtensions.map((ext) => ext.toUpperCase()).join(", ")}
					</>
				)}
			</>
		);
	};

	// Use acceptedTypes if provided, otherwise generate from allowed extensions
	// Include both MIME types and extensions for better macOS compatibility
	const inputAcceptedTypes =
		acceptedTypes ||
		(videoExtensions.length > 0 || audioExtensions.length > 0
			? generateAcceptAttribute([...videoExtensions, ...audioExtensions])
			: DEFAULT_ALLOWED_MIME_TYPES.join(","));

	return (
		<div className="space-y-2">
			<span className="morphio-caption block font-medium">
				Upload Media File
			</span>
			{/* biome-ignore lint/a11y/useSemanticElements: div required because this contains a child button (remove file), and button elements cannot contain other buttons per HTML spec */}
			<div
				role="button"
				tabIndex={isLoading || hasUrl ? -1 : 0}
				className={`w-full px-4 py-8 border-2 border-dashed rounded-xl text-center transition-all duration-200 ${
					inputFile
						? "border-green-500/50 dark:border-green-400/50 bg-green-50/90 dark:bg-green-500/5"
						: "border-gray-300 dark:border-gray-700/50 hover:border-gray-400 dark:hover:border-gray-600/50 bg-white/90 dark:bg-gray-900/50 backdrop-blur-xl shadow-xs"
				} ${
					isLoading || hasUrl
						? "opacity-50 cursor-not-allowed"
						: "cursor-pointer hover:bg-gray-50/90 dark:hover:bg-gray-800/50"
				}`}
				onClick={() => !isLoading && !hasUrl && fileInputRef.current?.click()}
				onKeyDown={(e) => {
					if ((e.key === "Enter" || e.key === " ") && !isLoading && !hasUrl) {
						e.preventDefault();
						fileInputRef.current?.click();
					}
				}}
				onDragOver={(e) => {
					e.preventDefault();
					e.stopPropagation();
				}}
				onDrop={handleDrop}
				aria-disabled={isLoading || hasUrl}
			>
				{inputFile ? (
					<div className="space-y-2">
						<div className="flex items-center justify-center text-green-600 dark:text-green-400">
							<FaCheckCircle className="h-8 w-8" />
						</div>
						<div className="morphio-body-sm text-gray-600 dark:text-gray-400">
							{inputFile.name}
						</div>
						<button
							type="button"
							onClick={(e) => {
								e.stopPropagation();
								setInputFile(null);
								if (fileInputRef.current) {
									fileInputRef.current.value = "";
								}
							}}
							className="morphio-body-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
						>
							Remove file
						</button>
					</div>
				) : (
					<div className="space-y-2">
						<div className="flex items-center justify-center text-gray-400 dark:text-gray-600">
							<FaUpload className="h-8 w-8" />
						</div>
						<div className="morphio-body-sm text-gray-600 dark:text-gray-400">
							Click to upload or drag and drop
						</div>
						<div className="morphio-caption text-gray-500 dark:text-gray-500">
							{getHelpText()}
						</div>
					</div>
				)}
			</div>
			<input
				ref={fileInputRef}
				type="file"
				accept={inputAcceptedTypes}
				onChange={handleFileChange}
				className="hidden"
				disabled={isLoading || hasUrl}
			/>
		</div>
	);
};

export default FileUpload;
