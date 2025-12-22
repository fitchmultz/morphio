/**
 * Standard API response wrapper type matching backend ApiResponse
 */
export interface ApiResponse<T> {
	status: "success" | "error";
	message: string;
	data?: T;
	timestamp?: string;
	correlation_id?: string;
}

/**
 * Type guard to check if a response is an ApiResponse wrapper
 * Checks for status being explicitly "success" or "error" for robustness
 */
export function isApiResponse<T>(
	response: unknown,
): response is ApiResponse<T> {
	return (
		response !== null &&
		typeof response === "object" &&
		"status" in response &&
		((response as { status: unknown }).status === "success" ||
			(response as { status: unknown }).status === "error")
	);
}

/**
 * Unwrap an API response to get just the data
 * Handles both wrapped ApiResponse and raw data
 */
export function unwrapApiResponse<T>(response: ApiResponse<T> | T): T {
	if (isApiResponse<T>(response)) {
		if (response.status === "error") {
			throw new Error(response.message || "API error");
		}
		return response.data as T;
	}
	return response as T;
}
