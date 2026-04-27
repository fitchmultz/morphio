/**
 * Auth configuration for the @hey-api SDK client.
 * Uses the built-in `auth` function in setConfig() for token management.
 *
 * This file is NOT auto-generated and won't be overwritten.
 */

import { client } from "@/client/client.gen";
import { API_BASE_URL } from "@/utils/constants";

// Track whether we've fired a logout event to avoid duplicates
let logoutEventFired = false;

/**
 * Get the current auth token from localStorage
 */
export function getAuthToken(): string | undefined {
	if (typeof window === "undefined") {
		return undefined;
	}
	return localStorage.getItem("access_token") ?? undefined;
}

/**
 * Configure the client with base URL and auth function.
 * Call this once on app initialization.
 */
export function initializeAuth(): void {
	client.setConfig({
		baseUrl: API_BASE_URL,
		credentials: "include",
		auth: () => getAuthToken(),
	});
}

/**
 * Set the auth token for API requests
 */
export function setAuthToken(token: string): void {
	if (typeof window !== "undefined") {
		localStorage.setItem("access_token", token);
	}
	// Re-apply config to ensure auth function picks up new token
	client.setConfig({
		baseUrl: API_BASE_URL,
		credentials: "include",
		auth: () => getAuthToken(),
	});
}

/**
 * Clear the auth token and dispatch logout event
 */
export function clearAuthToken(): void {
	if (typeof window !== "undefined") {
		localStorage.removeItem("access_token");
		if (!logoutEventFired) {
			logoutEventFired = true;
			window.dispatchEvent(new Event("auth:logout"));
		}
	}
	// Clear auth by setting it to return undefined
	client.setConfig({
		baseUrl: API_BASE_URL,
		credentials: "include",
		auth: () => undefined,
	});
}

/**
 * Reset the logout event flag (call after successful login)
 */
export function resetLogoutEventFlag(): void {
	logoutEventFired = false;
}

// Initialize on module load (client-side only)
if (typeof window !== "undefined") {
	initializeAuth();
}
