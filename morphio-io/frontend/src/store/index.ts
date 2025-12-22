import type { StateCreator } from "zustand";
import { persist } from "zustand/middleware";

// Define the store slice types
export interface UIStore {
	isDarkMode: boolean;
	setDarkMode: (isDark: boolean) => void;
}

// Create store slice creators
export const createUISlice: StateCreator<
	UIStore,
	[],
	[["zustand/persist", { isDarkMode: boolean }]]
> = persist(
	(set) => ({
		isDarkMode:
			typeof window !== "undefined"
				? window.matchMedia("(prefers-color-scheme: dark)").matches
				: false,
		setDarkMode: (isDark: boolean) => set({ isDarkMode: isDark }),
	}),
	{
		name: "ui-storage",
		partialize: (state) => ({ isDarkMode: state.isDarkMode }),
	},
);
