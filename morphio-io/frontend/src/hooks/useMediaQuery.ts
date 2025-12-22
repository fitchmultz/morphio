"use client";

import { useEffect, useState } from "react";

export const useMediaQuery = (query: string): boolean => {
	const [matches, setMatches] = useState(false);

	useEffect(() => {
		// Guard for SSR - window may not be available
		if (typeof window === "undefined") return;

		const media = window.matchMedia(query);
		// Set initial value
		setMatches(media.matches);

		const listener = (event: MediaQueryListEvent) => setMatches(event.matches);
		media.addEventListener("change", listener);

		return () => media.removeEventListener("change", listener);
	}, [query]); // Remove 'matches' from deps to avoid unnecessary re-subscriptions

	return matches;
};

// Predefined breakpoints
export const useIsMobile = () => useMediaQuery("(max-width: 640px)");
export const useIsTablet = () =>
	useMediaQuery("(min-width: 641px) and (max-width: 1024px)");
export const useIsDesktop = () => useMediaQuery("(min-width: 1025px)");
