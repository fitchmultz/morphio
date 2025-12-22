import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";
import { useUIStore } from "@/store/slices/uiSlice";

export const useDarkMode = () => {
	const { isDarkMode, setDarkMode } = useUIStore();
	const { theme, setTheme, systemTheme } = useTheme();
	const initialSyncDone = useRef(false);

	// Sync theme with store on mount and system preference changes
	useEffect(() => {
		if (!initialSyncDone.current) {
			const prefersDark = systemTheme === "dark";
			const currentTheme = theme === "system" ? prefersDark : theme === "dark";

			if (currentTheme !== isDarkMode) {
				setDarkMode(currentTheme);
			}
			initialSyncDone.current = true;
		}
	}, [theme, systemTheme, isDarkMode, setDarkMode]);

	// Sync store changes with theme
	useEffect(() => {
		if (initialSyncDone.current) {
			setTheme(isDarkMode ? "dark" : "light");
		}
	}, [isDarkMode, setTheme]);

	// Listen for system preference changes
	useEffect(() => {
		const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
		const handleChange = (e: MediaQueryListEvent) => {
			if (theme === "system") {
				setDarkMode(e.matches);
			}
		};

		mediaQuery.addEventListener("change", handleChange);
		return () => mediaQuery.removeEventListener("change", handleChange);
	}, [theme, setDarkMode]);

	const toggleDarkMode = () => {
		setDarkMode(!isDarkMode);
	};

	return {
		isDarkMode,
		toggleDarkMode,
	};
};
