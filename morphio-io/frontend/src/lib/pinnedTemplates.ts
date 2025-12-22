import logger from "@/lib/logger";

export type PinnedTemplateIds = number[];

const LOCAL_STORAGE_KEY = "pinnedTemplateIds";

/**
 * Check if we're in a browser environment
 */
function isBrowser(): boolean {
	return typeof window !== "undefined";
}

/**
 * Returns an array of pinned template IDs from localStorage
 */
export function getPinnedTemplateIds(): number[] {
	if (!isBrowser()) return [];
	try {
		const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
		if (stored) {
			return JSON.parse(stored) as number[];
		}
	} catch (error) {
		logger.warn("Failed to parse pinned templates:", { error });
	}
	return [];
}

/**
 * Checks if a given template ID is pinned
 */
export function isTemplatePinned(templateId: number): boolean {
	const pinned = getPinnedTemplateIds();
	return pinned.includes(templateId);
}

/**
 * Pins a given template ID by adding it to localStorage
 */
export function pinTemplate(templateId: number): void {
	if (!isBrowser()) return;
	const pinned = getPinnedTemplateIds();
	if (!pinned.includes(templateId)) {
		pinned.push(templateId);
		localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(pinned));
	}
}

/**
 * Unpins a given template ID by removing it from localStorage
 */
export function unpinTemplate(templateId: number): void {
	if (!isBrowser()) return;
	const pinned = getPinnedTemplateIds();
	const filtered = pinned.filter((id) => id !== templateId);
	localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(filtered));
}

/**
 * Toggles the pinned state of a template ID
 */
export function togglePinTemplate(templateId: number): void {
	if (isTemplatePinned(templateId)) {
		unpinTemplate(templateId);
	} else {
		pinTemplate(templateId);
	}
}
