/**
 * Media-related constants and enums
 */

export enum ContentSource {
	UPLOAD = "upload",
	YOUTUBE = "youtube",
	RUMBLE = "rumble",
	TWITTER = "twitter",
	TIKTOK = "tiktok",
	SPOTIFY = "spotify",
	WEB = "web",
}

export enum MediaType {
	VIDEO = "video",
	AUDIO = "audio",
	LOGS = "logs",
}

/**
 * Input for unified content processing
 */
export interface UnifiedProcessingInput {
	template_id: number | string;
	model: string;
	source: ContentSource;
	file: File | null;
	url: string;
	media_type?: MediaType;
}
