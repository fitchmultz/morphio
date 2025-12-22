import { ContentSource, MediaType } from "@/constants/media";

// Default video extensions to use if the dynamic ones aren't available
const DEFAULT_VIDEO_EXTENSIONS = [
	"mp4",
	"m4v",
	"mov",
	"avi",
	"wmv",
	"flv",
	"mkv",
	"webm",
	"mpeg",
	"mpg",
	"3gp",
	"ogg",
];

// Default audio extensions to use if the dynamic ones aren't available
const DEFAULT_AUDIO_EXTENSIONS = [
	"mp3",
	"wav",
	"m4a",
	"aac",
	"flac",
	"wma",
	"ogg",
];

/**
 * Detect the source (platform) of a URL
 * @param url URL to analyze
 * @returns ContentSource type
 */
export function detectUrlSource(url: string): ContentSource {
	const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
	const rumbleRegex = /^(https?:\/\/)?(www\.)?(rumble\.com)\/.+$/;
	const twitterRegex = /^(https?:\/\/)?(www\.)?(x\.com|twitter\.com)\/.+$/;
	const tiktokRegex =
		/^(https?:\/\/)?(www\.)?(tiktok\.com|vm\.tiktok\.com)\/.+$/;
	const spotifyRegex = /^(https?:\/\/)?((?:open|play)\.)?spotify\.com\//i;

	if (youtubeRegex.test(url)) return ContentSource.YOUTUBE;
	if (rumbleRegex.test(url)) return ContentSource.RUMBLE;
	if (twitterRegex.test(url)) return ContentSource.TWITTER;
	if (tiktokRegex.test(url)) return ContentSource.TIKTOK;
	if (spotifyRegex.test(url)) return ContentSource.SPOTIFY;
	return ContentSource.WEB;
}

/**
 * Automatically detect and select media type based on URL
 * @param url URL to analyze
 * @returns MediaType or null if can't be determined
 */
export function autoSelectMediaTypeForUrl(url: string): MediaType | null {
	const source = detectUrlSource(url);
	if (
		source === ContentSource.YOUTUBE ||
		source === ContentSource.RUMBLE ||
		source === ContentSource.TWITTER ||
		source === ContentSource.TIKTOK
	) {
		return MediaType.VIDEO;
	} else if (source === ContentSource.SPOTIFY) {
		return MediaType.AUDIO;
	}
	return null;
}

/**
 * Detect the type of file (video, audio, or unknown)
 * @param file File to analyze
 * @returns 'video', 'audio', or 'unknown'
 */
export function detectFileType(file: File): "video" | "audio" | "unknown" {
	if (!file || !file.type) return "unknown";

	if (file.type.startsWith("video/")) {
		return "video";
	} else if (file.type.startsWith("audio/")) {
		return "audio";
	}

	return "unknown";
}

/**
 * Map file extensions to their MIME types
 * This is used to improve macOS file picker compatibility
 */
export function getMimeTypeForExtension(ext: string): string | null {
	const mimeMap: Record<string, string> = {
		// Video formats
		mp4: "video/mp4",
		m4v: "video/x-m4v",
		mov: "video/quicktime",
		avi: "video/x-msvideo",
		wmv: "video/x-ms-wmv",
		flv: "video/x-flv",
		mkv: "video/x-matroska",
		webm: "video/webm",
		mpeg: "video/mpeg",
		mpg: "video/mpeg",
		"3gp": "video/3gpp",
		ogg: "video/ogg",
		// Audio formats
		mp3: "audio/mpeg",
		wav: "audio/wav",
		m4a: "audio/mp4",
		aac: "audio/aac",
		flac: "audio/flac",
		wma: "audio/x-ms-wma",
	};

	return mimeMap[ext.toLowerCase()] || null;
}

/**
 * Generate accept attribute value with both MIME types and extensions
 * This improves compatibility with macOS Finder file picker
 */
export function generateAcceptAttribute(extensions: string[]): string {
	const acceptValues: string[] = [];

	extensions.forEach((ext) => {
		const cleanExt = ext.toLowerCase().replace(/^\./, "");
		const mimeType = getMimeTypeForExtension(cleanExt);

		if (mimeType) {
			acceptValues.push(mimeType);
		}
		acceptValues.push(`.${cleanExt}`);
	});

	return acceptValues.join(",");
}

/**
 * Guess the media type from a file's extension
 * @param file File to analyze
 * @param videoExtensions Optional list of video extensions to check against
 * @param audioExtensions Optional list of audio extensions to check against
 * @returns MediaType based on file extension, or null if unknown
 */
export function guessMediaType(
	file: File,
	videoExtensions: string[] = DEFAULT_VIDEO_EXTENSIONS,
	audioExtensions: string[] = DEFAULT_AUDIO_EXTENSIONS,
): MediaType | null {
	const extension = file.name.split(".").pop()?.toLowerCase() || "";

	if (videoExtensions.includes(extension)) {
		return MediaType.VIDEO;
	} else if (audioExtensions.includes(extension)) {
		return MediaType.AUDIO;
	}

	return null;
}
