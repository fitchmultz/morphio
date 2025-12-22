"use client";

import { Moon, Sun } from "lucide-react";
import { type JSX, useEffect, useState } from "react";
import { useDarkMode } from "@/hooks/useDarkMode";
import logger from "@/lib/logger";

export const DarkModeToggle = (): JSX.Element => {
	// Call hook unconditionally
	const { isDarkMode, toggleDarkMode } = useDarkMode();
	const [mounted, setMounted] = useState(false);

	useEffect(() => {
		setMounted(true);
	}, []);

	const handleToggle = () => {
		toggleDarkMode();
		logger.info("Theme toggled", { newMode: !isDarkMode });
	};

	// Conditionally render only the output
	if (!mounted) {
		// Render a placeholder so SSR doesn't mismatch
		return <div style={{ width: "40px", height: "40px" }} />;
	}

	return (
		<button
			type="button"
			onClick={handleToggle}
			className="morphio-icon-button h-10 w-10 inline-flex items-center justify-center rounded-xl bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700/80 border border-gray-200/50 dark:border-gray-700/50 hover:shadow-md"
			aria-label="Toggle Dark Mode"
		>
			<div className="relative h-5 w-5">
				<span
					className={`absolute inset-0 flex items-center justify-center transform transition-all duration-300 ${
						isDarkMode ? "rotate-0 opacity-100" : "rotate-90 opacity-0"
					}`}
				>
					<Moon
						className="h-5 w-5 text-blue-600 dark:text-blue-400"
						strokeWidth={2}
					/>
				</span>
				<span
					className={`absolute inset-0 flex items-center justify-center transform transition-all duration-300 ${
						isDarkMode ? "-rotate-90 opacity-0" : "rotate-0 opacity-100"
					}`}
				>
					<Sun
						className="h-5 w-5 text-yellow-600 dark:text-yellow-400"
						strokeWidth={2}
					/>
				</span>
			</div>
			<span className="sr-only">Toggle Dark Mode</span>
		</button>
	);
};
