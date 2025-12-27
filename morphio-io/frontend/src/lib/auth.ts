/**
 * Auth API functions (pure API calls, no side effects)
 *
 * All state management (localStorage, navigation) is handled by AuthContext.
 * These functions only make API calls and return results.
 */

import {
	login as loginSdk,
	logout as logoutSdk,
	register as registerSdk,
} from "@/client/sdk.gen";
import type { UserOut } from "@/client/types.gen";
import { clearAuthToken } from "@/lib/hey-api";
import eventEmitter from "./eventEmitter";
import logger from "./logger";

export type AuthResult = {
	access_token: string;
	user: UserOut;
};

export const login = async (
	email: string,
	password: string,
): Promise<AuthResult> => {
	const response = await loginSdk({
		body: { email, password },
	});

	const payload = response.data?.data;
	if (payload?.access_token && payload?.user) {
		return {
			access_token: payload.access_token,
			user: payload.user,
		};
	}

	// Handle error response
	const errorMessage =
		response.error &&
		typeof response.error === "object" &&
		"message" in response.error
			? String(response.error.message)
			: response.data?.message || "Login failed";
	throw new Error(errorMessage);
};

export const register = async (
	email: string,
	password: string,
	displayName: string,
): Promise<AuthResult> => {
	const response = await registerSdk({
		body: { email, password, display_name: displayName },
	});

	const payload = response.data?.data;
	if (payload?.access_token && payload?.user) {
		return {
			access_token: payload.access_token,
			user: payload.user,
		};
	}

	// Handle error response
	const errorMessage =
		response.error &&
		typeof response.error === "object" &&
		"message" in response.error
			? String(response.error.message)
			: response.data?.message || "Registration failed";
	throw new Error(errorMessage);
};

export const logout = async (): Promise<void> => {
	try {
		await logoutSdk();
	} catch (error) {
		logger.error("Error during logout", { error });
	} finally {
		clearAuthToken();
		eventEmitter.emit("logout");
	}
};
