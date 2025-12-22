import { create } from "zustand";
import { createUISlice, type UIStore } from "../index";

export const useUIStore = create<UIStore>()((...args) => ({
	...createUISlice(...args),
}));
