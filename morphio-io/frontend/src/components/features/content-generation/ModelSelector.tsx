import { type FC, useEffect, useState } from "react";
import { FaChevronDown } from "react-icons/fa";
import { getAvailableModels } from "@/client/sdk.gen";
import logger from "@/lib/logger";

interface ModelInfo {
	id: string;
	label: string;
}

// Fallback models if API fails
const FALLBACK_MODELS: ModelInfo[] = [
	{ id: "gemini-3-flash-preview", label: "Gemini 3 Flash (High)" },
	{ id: "gemini-3-flash-preview-medium", label: "Gemini 3 Flash (Medium)" },
	{ id: "gemini-3-flash-preview-low", label: "Gemini 3 Flash (Low)" },
	{ id: "gemini-3-flash-preview-minimal", label: "Gemini 3 Flash (Minimal)" },
	{ id: "gemini-3-pro-preview", label: "Gemini 3 Pro (High)" },
	{ id: "gemini-3-pro-preview-low", label: "Gemini 3 Pro (Low)" },
	{ id: "gpt-5.1", label: "GPT-5.1" },
	{ id: "gpt-5.1-high", label: "GPT-5.1 (High Reasoning)" },
	{ id: "gpt-5.1-medium", label: "GPT-5.1 (Medium Reasoning)" },
	{ id: "gpt-5.1-low", label: "GPT-5.1 (Low Reasoning)" },
	{ id: "claude-4-sonnet", label: "Claude 4 Sonnet" },
];

interface ModelSelectorProps {
	selectedModel: string;
	onModelChange: (modelId: string) => void;
	isLoading: boolean;
}

const ModelSelector: FC<ModelSelectorProps> = ({
	selectedModel,
	onModelChange,
	isLoading,
}) => {
	const [models, setModels] = useState<ModelInfo[]>(FALLBACK_MODELS);

	useEffect(() => {
		const isValidModelInfo = (item: unknown): item is ModelInfo =>
			typeof item === "object" &&
			item !== null &&
			typeof (item as ModelInfo).id === "string" &&
			typeof (item as ModelInfo).label === "string";

		const fetchModels = async () => {
			try {
				const { data } = await getAvailableModels();
				if (
					data?.status === "success" &&
					Array.isArray(data.data) &&
					data.data.every(isValidModelInfo)
				) {
					setModels(data.data);
				} else if (data?.status === "success") {
					logger.warn(
						"Fetched models data has incorrect shape, using fallback",
					);
				}
			} catch (error: unknown) {
				const msg = error instanceof Error ? error.message : "Unknown error";
				logger.warn("Failed to fetch models, using fallback", { error: msg });
			}
		};

		fetchModels();
	}, []);

	return (
		<div className="space-y-2">
			<label className="morphio-caption block font-medium">
				Select AI Model
				<div className="relative mt-2">
					<select
						value={selectedModel}
						onChange={(e) => onModelChange(e.target.value)}
						className="morphio-input appearance-none"
						disabled={isLoading}
					>
						{models.map((model) => (
							<option key={model.id} value={model.id}>
								{model.label}
							</option>
						))}
					</select>
					<div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
						<FaChevronDown className="text-gray-400" />
					</div>
				</div>
			</label>
		</div>
	);
};

export default ModelSelector;
