export const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_BASE_URL ||
	(process.env.NODE_ENV === "production"
		? "https://api.morphio.io"
		: "http://localhost:8000");

export const ROUTES = {
	HOME: "/",
	LOGIN: "/login",
	REGISTER: "/register",
	DASHBOARD: "/dashboard",
	PROFILE: "/profile",
	CONTENT: "/content",
	TEMPLATES: "/templates",
} as const;

export const AUTH_COOKIE_NAME = "auth_token";

export const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

// Note: These are fallback values. The application now
// dynamically fetches allowed media extensions from the backend.
// See getMediaFileConfiguration in api.ts
export const SUPPORTED_VIDEO_FORMATS = [
	"video/mp4",
	"video/webm",
	"video/ogg",
] as const;

// Audio fallback formats
export const SUPPORTED_AUDIO_FORMATS = [
	"audio/mpeg",
	"audio/mp3",
	"audio/wav",
	"audio/aac",
	"audio/flac",
] as const;
