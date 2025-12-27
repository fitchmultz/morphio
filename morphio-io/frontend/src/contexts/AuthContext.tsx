"use client";

import { jwtDecode } from "jwt-decode";
import { useRouter } from "next/navigation";
import type React from "react";
import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useEffect,
	useRef,
	useState,
} from "react";
import type { UserOut } from "@/client/types.gen";
import eventEmitter from "@/lib/eventEmitter";
import { resetLogoutEventFlag } from "@/lib/hey-api";
import logger from "@/lib/logger";
import { notifyError, notifySuccess } from "@/lib/toast";
import { API_BASE_URL } from "@/utils/constants";

// Interface for decoded JWT token
interface DecodedToken {
	sub: string;
	exp: number;
	iat: number;
	type: string;
}

// Enhanced interface with token management
interface AuthContextType {
	isAuthenticated: boolean;
	login: (token: string, userData: UserOut) => void;
	logout: (message?: string) => void;
	loading: boolean;
	userData: UserOut | null;
	updateUserData: (newData: Partial<UserOut>) => void;
	getToken: () => string | null;
	handleSessionExpired: () => void;
	clearUserData: () => void;
	checkTokenValidity: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({
	children,
}) => {
	const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
	const [loading, setLoading] = useState<boolean>(true);
	const [userData, setUserData] = useState<UserOut | null>(null);
	const router = useRouter();
	const pendingLogoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const csrfTokenRef = useRef<string | null>(null);

	// Define clearUserData first
	const clearUserData = useCallback(() => {
		setUserData(null);
		setIsAuthenticated(false);
		localStorage.removeItem("access_token");
		localStorage.removeItem("userData");
		eventEmitter.emit("userDataCleared");
		logger.info("User data cleared");
	}, []);

	// Debounced version of logout to prevent multiple notifications
	const debouncedLogout = useCallback(
		(message = "Your session has expired. Please log in again.") => {
			return new Promise<void>((resolve) => {
				// Cancel any existing pending logout
				if (pendingLogoutRef.current !== null) {
					clearTimeout(pendingLogoutRef.current);
				}
				pendingLogoutRef.current = setTimeout(async () => {
					pendingLogoutRef.current = null;

					// Call server logout to revoke refresh token cookie
					const token = localStorage.getItem("access_token");
					if (token) {
						try {
							await fetch(`${API_BASE_URL}/auth/logout`, {
								method: "POST",
								credentials: "include",
								headers: {
									Authorization: `Bearer ${token}`,
								},
							});
						} catch (error) {
							// Continue with local cleanup even if server call fails
							logger.debug("Server logout call failed", { error });
						}
					}

					clearUserData();
					router.push("/");
					if (message === "Successfully logged out") {
						notifySuccess(message);
					} else {
						notifyError(message);
					}
					logger.info("User logged out", { reason: message });
					resolve();
				}, 300);
			});
		},
		[router, clearUserData],
	);

	const logout = useCallback(
		(message = "Your session has expired. Please log in again.") => {
			debouncedLogout(message);
		},
		[debouncedLogout],
	);

	const handleSessionExpired = useCallback(() => {
		logout("Your session has expired. Please log in again.");
		logger.info("Session expired, user logged out");
	}, [logout]);

	const isValidUserData = useCallback((data: unknown): data is UserOut => {
		return (
			typeof data === "object" &&
			data !== null &&
			"id" in data &&
			"email" in data &&
			"display_name" in data &&
			typeof (data as UserOut).id === "number" &&
			typeof (data as UserOut).email === "string" &&
			typeof (data as UserOut).display_name === "string"
		);
	}, []);

	// Check if token is valid
	const checkTokenValidity = useCallback((): boolean => {
		// Guard against SSR - localStorage is not available on server
		if (typeof window === "undefined") return false;

		const token = localStorage.getItem("access_token");
		if (!token) return false;

		try {
			const decoded = jwtDecode<DecodedToken>(token);

			// Check if token is expired
			if (decoded.exp < Date.now() / 1000) {
				logger.info("Access token has expired");
				return false;
			}

			// Check if it's an access token
			if (decoded.type !== "access") {
				logger.warn("Invalid token type in access token");
				return false;
			}

			return true;
		} catch (error) {
			// Expected for unauthenticated users with no/invalid token
			logger.debug("Could not decode access token", { error });
			return false;
		}
	}, []);

	useEffect(() => {
		const token = localStorage.getItem("access_token");
		if (token) {
			if (checkTokenValidity()) {
				setIsAuthenticated(true);
				logger.info("User authenticated on page load");
				try {
					const storedUserData = localStorage.getItem("userData");
					if (storedUserData) {
						const parsedUserData = JSON.parse(storedUserData);
						if (isValidUserData(parsedUserData)) {
							setUserData(parsedUserData);
						} else {
							throw new Error("Invalid user data structure.");
						}
					}
				} catch (error) {
					// Silent clear for boot-time recovery - let route guards handle navigation
					logger.warn("Could not parse stored userData, clearing auth state", {
						error,
					});
					clearUserData();
				}
			} else {
				// Token exists but is invalid - silent clear, no toast on boot
				logger.info("Invalid token found on page load, clearing auth state");
				clearUserData();
			}
		} else {
			logger.info("No authentication token found on page load");
		}
		setLoading(false);
	}, [checkTokenValidity, isValidUserData, clearUserData]);

	const login = useCallback(
		(token: string, newUserData: UserOut) => {
			// Cancel any pending logout (prevents race condition with session expired toast)
			if (pendingLogoutRef.current !== null) {
				clearTimeout(pendingLogoutRef.current);
				pendingLogoutRef.current = null;
			}
			localStorage.setItem("access_token", token);
			localStorage.setItem("userData", JSON.stringify(newUserData));
			setIsAuthenticated(true);
			setUserData(newUserData);
			resetLogoutEventFlag();
			router.push("/dashboard");
			logger.info("User logged in", { userId: newUserData.id });
		},
		[router],
	);

	const updateUserData = useCallback((newData: Partial<UserOut>) => {
		setUserData((prevData) => {
			if (prevData) {
				const updatedData = { ...prevData, ...newData };
				localStorage.setItem("userData", JSON.stringify(updatedData));
				return updatedData;
			}
			return prevData;
		});
		logger.info("User data updated", { updatedFields: Object.keys(newData) });
	}, []);

	const getToken = useCallback(() => localStorage.getItem("access_token"), []);

	// Clean up pending logout timeout on unmount
	useEffect(() => {
		return () => {
			if (pendingLogoutRef.current !== null) {
				clearTimeout(pendingLogoutRef.current);
				pendingLogoutRef.current = null;
			}
		};
	}, []);

	// Listen for global logout events
	useEffect(() => {
		const handleLogoutEvent = () => {
			handleSessionExpired();
		};

		eventEmitter.on("logout", handleLogoutEvent);

		return () => {
			eventEmitter.off("logout", handleLogoutEvent);
		};
	}, [handleSessionExpired]);

	// Helper to fetch CSRF token for refresh requests
	const ensureCsrfToken = useCallback(async (): Promise<string | null> => {
		if (csrfTokenRef.current) {
			return csrfTokenRef.current;
		}

		try {
			const response = await fetch(`${API_BASE_URL}/auth/csrf-token`, {
				method: "GET",
				credentials: "include",
			});

			if (response.ok) {
				const data = await response.json();
				const token = data.data?.csrf_token;
				if (token) {
					csrfTokenRef.current = token;
					return token;
				}
			}
		} catch (error) {
			logger.debug("Could not fetch CSRF token", { error });
		}

		return null;
	}, []);

	// Set up proactive token refresh
	useEffect(() => {
		if (!isAuthenticated) return;

		const refreshAccessToken = async () => {
			try {
				const token = localStorage.getItem("access_token");
				if (!token) return;

				// Decode token to check when it expires
				try {
					const decoded = jwtDecode<DecodedToken>(token);

					// Calculate time until expiry (in milliseconds)
					const expiresIn = decoded.exp * 1000 - Date.now();

					// If token expires in less than 5 minutes (300000ms), refresh it
					if (expiresIn < 300000 && expiresIn > 0) {
						logger.info("Proactively refreshing access token");

						// Fetch CSRF token for the refresh request
						const csrfToken = await ensureCsrfToken();

						const headers: HeadersInit = {};
						if (csrfToken) {
							headers["X-CSRF-Token"] = csrfToken;
						}

						const response = await fetch(`${API_BASE_URL}/auth/refresh-token`, {
							method: "POST",
							credentials: "include",
							headers,
						});

						const data = await response.json();

						if (
							response.ok &&
							data.status === "success" &&
							data.data?.access_token
						) {
							localStorage.setItem("access_token", data.data.access_token);
							logger.info("Access token refreshed proactively");
						} else if (response.status === 403) {
							// CSRF token may have expired, clear and retry on next interval
							csrfTokenRef.current = null;
							logger.debug("CSRF token may have expired, will retry");
						}
					}
				} catch (error) {
					logger.debug("Could not decode token for refresh check", { error });
				}
			} catch (error) {
				logger.error("Error in proactive token refresh", { error });
			}
		};

		// Check token every minute
		const refreshInterval = setInterval(refreshAccessToken, 60000);

		// Initial check
		refreshAccessToken();

		return () => clearInterval(refreshInterval);
	}, [isAuthenticated, ensureCsrfToken]);

	return (
		<AuthContext.Provider
			value={{
				isAuthenticated,
				login,
				logout,
				loading,
				userData,
				updateUserData,
				getToken,
				handleSessionExpired,
				clearUserData,
				checkTokenValidity,
			}}
		>
			{children}
		</AuthContext.Provider>
	);
};

export const useAuth = (): AuthContextType => {
	const context = useContext(AuthContext);
	if (!context) {
		throw new Error("useAuth must be used within an AuthProvider");
	}
	return context;
};
