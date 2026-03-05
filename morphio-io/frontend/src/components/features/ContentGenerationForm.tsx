import {
	type FC,
	type FormEvent,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import { FaChevronDown, FaChevronUp } from "react-icons/fa";
import { getMediaConfig } from "@/client/sdk.gen";
import type { TemplateOut } from "@/client/types.gen";
import {
	ContentSource,
	MediaType,
	type UnifiedProcessingInput,
} from "@/constants/media";
import logger from "@/lib/logger";
import { getPinnedTemplateIds } from "@/lib/pinnedTemplates";
import { notifyError } from "@/lib/toast";
import { detectFileType, detectUrlSource } from "@/utils/mediaUtils";
import DiarizationControls, {
	type DiarizationSettings,
} from "./content-generation/DiarizationControls";
import FileUpload from "./content-generation/FileUpload";
import FormProgress from "./content-generation/FormProgress";
import ModelSelector from "./content-generation/ModelSelector";
import TemplateSelector from "./content-generation/TemplateSelector";
// Import sub-components
import UrlInput from "./content-generation/UrlInput";

interface ContentGenerationFormProps {
	onSubmit: (input: UnifiedProcessingInput) => Promise<void>;
	templates: { custom: TemplateOut[]; default: TemplateOut[] };
	isLoading: boolean;
	error?: string | null;
	progress?: number;
	stage?: string | null;
	statusMessage?: string;
	resetFormTrigger?: number;
}

const ContentGenerationFormComponent: FC<ContentGenerationFormProps> = ({
	onSubmit,
	templates,
	isLoading,
	error,
	progress,
	stage,
	statusMessage,
	resetFormTrigger,
}) => {
	const [inputUrl, setInputUrl] = useState<string>("");
	const [inputFile, setInputFile] = useState<File | null>(null);
	const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
	const [selectedModel, setSelectedModel] = useState<string>(
		"gemini-3-flash-preview",
	);
	const [autoDetectedType, setAutoDetectedType] = useState<MediaType | null>(
		null,
	);
	const [diarizationSettings, setDiarizationSettings] =
		useState<DiarizationSettings>({
			enabled: false,
			minSpeakers: null,
			maxSpeakers: null,
		});
	const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);

	const fileInputRef = useRef<HTMLInputElement>(null);

	// Set a default value, but we'll try to get it from the API
	const [maxUploadSize, setMaxUploadSize] = useState<number>(
		parseInt(process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE || "3221225472", 10),
	);

	useEffect(() => {
		// Fetch the max upload size from the backend
		const fetchMaxUploadSize = async () => {
			try {
				const { data } = await getMediaConfig();
				if (data?.status === "success" && data.data) {
					const configData = data.data as Record<string, unknown>;
					if (configData.max_upload_size) {
						setMaxUploadSize(configData.max_upload_size as number);
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

	const getPinnedAndSortedTemplates = useCallback(
		(templatesArr: TemplateOut[]): TemplateOut[] => {
			const pinnedIds = getPinnedTemplateIds();
			const pinned = templatesArr
				.filter((t) => pinnedIds.includes(t.id))
				.sort((a, b) => a.name.localeCompare(b.name));
			const unpinned = templatesArr
				.filter((t) => !pinnedIds.includes(t.id))
				.sort((a, b) => a.name.localeCompare(b.name));
			return [...pinned, ...unpinned];
		},
		[],
	);

	const pinnedDefault = useMemo(
		() => getPinnedAndSortedTemplates(templates.default),
		[templates.default, getPinnedAndSortedTemplates],
	);
	const pinnedCustom = useMemo(
		() => getPinnedAndSortedTemplates(templates.custom),
		[templates.custom, getPinnedAndSortedTemplates],
	);

	useEffect(() => {
		if (resetFormTrigger) {
			setInputUrl("");
			setInputFile(null);
			if (fileInputRef.current) {
				fileInputRef.current.value = "";
			}
			setSelectedTemplate(null);
			setAutoDetectedType(null);
			setDiarizationSettings({
				enabled: false,
				minSpeakers: null,
				maxSpeakers: null,
			});
		}
	}, [resetFormTrigger]);

	useEffect(() => {
		if (selectedTemplate === null) {
			if (pinnedDefault.length > 0) {
				setSelectedTemplate(pinnedDefault[0].id);
			} else if (pinnedCustom.length > 0) {
				setSelectedTemplate(pinnedCustom[0].id);
			}
		}
	}, [selectedTemplate, pinnedDefault, pinnedCustom]);

	const handleTemplateChange = (templateId: number) => {
		setSelectedTemplate(templateId);
	};

	const handleModelChange = (modelId: string) => {
		setSelectedModel(modelId);
	};

	const handleSubmit = async (e: FormEvent) => {
		e.preventDefault();

		if (!selectedTemplate) {
			notifyError("Please select a template.");
			return;
		}

		if (!inputUrl && !inputFile) {
			notifyError("Please provide a URL or upload a file.");
			return;
		}

		// Determine source and file
		let source: ContentSource;
		if (inputUrl) {
			source = detectUrlSource(inputUrl);
		} else {
			source = ContentSource.UPLOAD;
		}

		// Determine media type
		let mediaType: MediaType | undefined;
		if (autoDetectedType) {
			mediaType = autoDetectedType;
		} else if (inputFile) {
			const fileType = detectFileType(inputFile);
			if (fileType === "video") {
				mediaType = MediaType.VIDEO;
			} else if (fileType === "audio") {
				mediaType = MediaType.AUDIO;
			}
		}

		const formData: UnifiedProcessingInput = {
			template_id: selectedTemplate,
			model: selectedModel,
			source,
			file: inputFile,
			url: inputUrl,
			...(mediaType && { media_type: mediaType }),
			...(diarizationSettings.enabled && {
				enable_diarization: true,
				min_speakers: diarizationSettings.minSpeakers,
				max_speakers: diarizationSettings.maxSpeakers,
			}),
		};

		try {
			await onSubmit(formData);
		} catch (error) {
			logger.warn("Form submission error", { error });
			// Error is handled by the parent component
		}
	};

	const isSubmitDisabled =
		isLoading || !selectedTemplate || (!inputUrl && !inputFile);

	return (
		<div className="w-full">
			<form onSubmit={handleSubmit} className="space-y-4">
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

				<TemplateSelector
					selectedTemplate={selectedTemplate}
					onTemplateChange={handleTemplateChange}
					pinnedDefault={pinnedDefault}
					pinnedCustom={pinnedCustom}
					isLoading={isLoading}
				/>

				{/* Advanced Options Toggle */}
				<button
					type="button"
					onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
					className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
				>
					{showAdvancedOptions ? (
						<FaChevronUp className="h-3 w-3" />
					) : (
						<FaChevronDown className="h-3 w-3" />
					)}
					<span>Advanced Options</span>
				</button>

				{/* Collapsible Advanced Options */}
				{showAdvancedOptions && (
					<div className="space-y-4 pl-4 border-l-2 border-gray-200 dark:border-gray-700">
						<ModelSelector
							selectedModel={selectedModel}
							onModelChange={handleModelChange}
							isLoading={isLoading}
						/>

						<DiarizationControls
							value={diarizationSettings}
							onChange={setDiarizationSettings}
							disabled={isLoading}
							visible={
								!!inputFile ||
								(!!inputUrl &&
									(autoDetectedType === MediaType.VIDEO ||
										autoDetectedType === MediaType.AUDIO))
							}
						/>
					</div>
				)}

				<button
					type="submit"
					className={`morphio-button w-full px-5 py-3.5 flex items-center justify-center space-x-2 ${
						isSubmitDisabled ? "opacity-50 cursor-not-allowed" : ""
					}`}
					disabled={isSubmitDisabled}
				>
					{isLoading ? "Processing..." : "Generate Content"}
				</button>

				<FormProgress
					isLoading={isLoading}
					progress={progress}
					stage={stage}
					statusMessage={statusMessage}
					error={error}
				/>
			</form>
		</div>
	);
};

export const ContentGenerationForm = ContentGenerationFormComponent;
