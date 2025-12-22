import type React from "react";
import { FaInfoCircle } from "react-icons/fa";

export interface DiarizationSettings {
	enabled: boolean;
	minSpeakers: number | null;
	maxSpeakers: number | null;
}

interface DiarizationControlsProps {
	value: DiarizationSettings;
	onChange: (settings: DiarizationSettings) => void;
	disabled?: boolean;
	visible: boolean;
}

const DiarizationControls: React.FC<DiarizationControlsProps> = ({
	value,
	onChange,
	disabled = false,
	visible,
}) => {
	if (!visible) return null;

	const handleEnabledChange = (enabled: boolean) => {
		onChange({ ...value, enabled });
	};

	const handleMinSpeakersChange = (minSpeakers: number | null) => {
		// Validate min <= max if both are set
		if (
			minSpeakers !== null &&
			value.maxSpeakers !== null &&
			minSpeakers > value.maxSpeakers
		) {
			// Auto-adjust max to match min
			onChange({ ...value, minSpeakers, maxSpeakers: minSpeakers });
		} else {
			onChange({ ...value, minSpeakers });
		}
	};

	const handleMaxSpeakersChange = (maxSpeakers: number | null) => {
		// Validate max >= min if both are set
		if (
			maxSpeakers !== null &&
			value.minSpeakers !== null &&
			maxSpeakers < value.minSpeakers
		) {
			// Auto-adjust min to match max
			onChange({ ...value, maxSpeakers, minSpeakers: maxSpeakers });
		} else {
			onChange({ ...value, maxSpeakers });
		}
	};

	return (
		<div className="space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-2">
					<label
						htmlFor="enable-diarization"
						className="morphio-body-sm font-medium"
					>
						Speaker Identification
					</label>
					<span
						title="Identifies and labels different speakers in your audio/video content. Useful for interviews, meetings, and multi-speaker recordings."
						className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help"
					>
						<FaInfoCircle className="h-3.5 w-3.5" />
					</span>
				</div>
				<label className="relative inline-flex items-center cursor-pointer">
					<input
						type="checkbox"
						id="enable-diarization"
						checked={value.enabled}
						onChange={(e) => handleEnabledChange(e.target.checked)}
						disabled={disabled}
						className="sr-only peer"
					/>
					<div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600" />
				</label>
			</div>

			{value.enabled && (
				<div className="flex gap-4 mt-3">
					<div className="flex-1">
						<label
							htmlFor="min-speakers"
							className="block text-xs text-gray-500 dark:text-gray-400 mb-1"
						>
							Min speakers (optional)
						</label>
						<input
							type="number"
							id="min-speakers"
							min={1}
							max={10}
							value={value.minSpeakers ?? ""}
							onChange={(e) =>
								handleMinSpeakersChange(
									e.target.value ? parseInt(e.target.value, 10) : null,
								)
							}
							disabled={disabled}
							placeholder="1"
							className="morphio-input w-full py-2 text-sm"
						/>
					</div>
					<div className="flex-1">
						<label
							htmlFor="max-speakers"
							className="block text-xs text-gray-500 dark:text-gray-400 mb-1"
						>
							Max speakers (optional)
						</label>
						<input
							type="number"
							id="max-speakers"
							min={1}
							max={10}
							value={value.maxSpeakers ?? ""}
							onChange={(e) =>
								handleMaxSpeakersChange(
									e.target.value ? parseInt(e.target.value, 10) : null,
								)
							}
							disabled={disabled}
							placeholder="10"
							className="morphio-input w-full py-2 text-sm"
						/>
					</div>
				</div>
			)}
		</div>
	);
};

export default DiarizationControls;
