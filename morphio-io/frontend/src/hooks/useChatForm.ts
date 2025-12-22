"use client";

import { useCallback, useState } from "react";

export interface UseChatFormOptions {
	maxLength?: number;
	onSubmit: (message: string) => Promise<void>;
}

export interface UseChatFormReturn {
	inputValue: string;
	setInputValue: (value: string) => void;
	handleSubmit: (e: React.FormEvent) => Promise<void>;
	handleChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
	isNearLimit: boolean;
	charactersRemaining: number;
	clearInput: () => void;
}

export function useChatForm({
	maxLength = 5000,
	onSubmit,
}: UseChatFormOptions): UseChatFormReturn {
	const [inputValue, setInputValue] = useState("");

	const charactersRemaining = maxLength - inputValue.length;
	const isNearLimit = charactersRemaining < 500;

	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			const value = e.target.value;
			if (value.length <= maxLength) {
				setInputValue(value);
			}
		},
		[maxLength],
	);

	const handleSubmit = useCallback(
		async (event: React.FormEvent) => {
			event.preventDefault();
			if (!inputValue.trim()) return;
			await onSubmit(inputValue);
		},
		[onSubmit, inputValue],
	);

	const clearInput = useCallback(() => {
		setInputValue("");
	}, []);

	return {
		inputValue,
		setInputValue,
		handleSubmit,
		handleChange,
		isNearLimit,
		charactersRemaining,
		clearInput,
	};
}
