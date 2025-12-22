"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo } from "react";
import { useAuth } from "@/contexts/AuthContext";
import eventEmitter from "@/lib/eventEmitter";

interface UseAuthGuardOptions {
	onUserDataCleared?: () => void;
	redirectPath?: string;
}

export function useAuthGuard(options: UseAuthGuardOptions = {}) {
	const {
		isAuthenticated,
		loading: authLoading,
		handleSessionExpired,
		checkTokenValidity,
		userData,
	} = useAuth();
	const router = useRouter();
	const onUserDataCleared = options.onUserDataCleared;
	const redirectPath = options.redirectPath || "/";

	// Redirect if not authenticated
	useEffect(() => {
		if (!authLoading && !isAuthenticated) {
			router.push(redirectPath);
		}
	}, [authLoading, isAuthenticated, router, redirectPath]);

	// Note: Token validity checks are centralized in AuthContext to avoid race conditions
	// AuthContext handles proactive token refresh every minute

	// Define stable callbacks for event handlers
	const handleLogout = useCallback(() => {
		handleSessionExpired();
		router.push(redirectPath);
	}, [handleSessionExpired, router, redirectPath]);

	const handleUserDataCleared = useCallback(() => {
		if (onUserDataCleared) {
			onUserDataCleared();
		}
	}, [onUserDataCleared]);

	// Listen for auth events
	useEffect(() => {
		eventEmitter.on("logout", handleLogout);
		eventEmitter.on("userDataCleared", handleUserDataCleared);

		return () => {
			eventEmitter.off("logout", handleLogout);
			eventEmitter.off("userDataCleared", handleUserDataCleared);
		};
	}, [handleLogout, handleUserDataCleared]);

	// Memoize token validity to avoid re-computing on every render
	const isTokenValid = useMemo(
		() => checkTokenValidity(),
		[checkTokenValidity],
	);

	return {
		isAuthenticated,
		isLoading: authLoading,
		isTokenValid,
		userData,
	};
}
