export const getApiErrorMessage = (
	error: unknown,
	fallback: string,
): string => {
	if (error instanceof Error) {
		return error.message;
	}

	if (error && typeof error === "object") {
		if ("detail" in error && error.detail) {
			return String(error.detail);
		}
		if ("message" in error && error.message) {
			return String(error.message);
		}
	}

	return fallback;
};
