import debounce from "lodash/debounce";
import type React from "react";
import { type ChangeEvent, useEffect, useMemo } from "react";
import { FaCheck, FaGlobe } from "react-icons/fa";
import { MediaType } from "@/constants/media";
import { autoSelectMediaTypeForUrl } from "@/utils/mediaUtils";

const getSourceLabel = (url: string): string | null => {
	if (!url) return null;
	try {
		const hostname = new URL(url).hostname.toLowerCase();
		if (hostname.includes("youtube.com") || hostname.includes("youtu.be"))
			return "YouTube video";
		if (hostname.includes("rumble.com")) return "Rumble video";
		if (hostname.includes("twitter.com") || hostname.includes("x.com"))
			return "X/Twitter video";
		if (hostname.includes("tiktok.com")) return "TikTok video";
		if (hostname.includes("spotify.com")) return "Spotify audio";
		if (hostname.includes("vimeo.com")) return "Vimeo video";
		// If it's a detected video URL but not a known source
		if (autoSelectMediaTypeForUrl(url) === MediaType.VIDEO) return "Video URL";
		if (autoSelectMediaTypeForUrl(url) === MediaType.AUDIO) return "Audio URL";
		return "Web content";
	} catch {
		return null;
	}
};

interface UrlInputProps {
	inputUrl: string;
	setInputUrl: (url: string) => void;
	setAutoDetectedType: (type: MediaType | null) => void;
	isLoading: boolean;
	hasFile: boolean;
}

const UrlInput: React.FC<UrlInputProps> = ({
	inputUrl,
	setInputUrl,
	setAutoDetectedType,
	isLoading,
	hasFile,
}) => {
	const debouncedAutoDetect = useMemo(
		() =>
			debounce((value: string) => {
				const detectedType = autoSelectMediaTypeForUrl(value);
				setAutoDetectedType(detectedType);
			}, 300),
		[setAutoDetectedType],
	);

	useEffect(() => {
		return () => {
			debouncedAutoDetect.cancel();
		};
	}, [debouncedAutoDetect]);

	const handleUrlChange = (e: ChangeEvent<HTMLInputElement>) => {
		const value = e.target.value;
		setInputUrl(value);
		debouncedAutoDetect(value);
	};

	return (
		<div className="space-y-2">
			<label className="morphio-caption block font-medium">
				<div className="flex items-center">
					<FaGlobe className="mr-2 text-gray-500" />
					Website or Media URL
				</div>
				<input
					type="url"
					placeholder="https://example.com/media"
					value={inputUrl}
					onChange={handleUrlChange}
					className={`morphio-input mt-2 ${
						isLoading || hasFile ? "opacity-50 cursor-not-allowed" : ""
					}`}
					disabled={isLoading || hasFile}
				/>
			</label>
			{inputUrl && getSourceLabel(inputUrl) && (
				<div className="morphio-caption flex items-center gap-2 text-green-600 dark:text-green-400">
					<FaCheck className="h-3 w-3" />
					<span>Detected: {getSourceLabel(inputUrl)}</span>
				</div>
			)}
		</div>
	);
};

export default UrlInput;
