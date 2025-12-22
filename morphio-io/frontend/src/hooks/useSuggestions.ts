"use client";

import { useMemo } from "react";

const BASE_SUGGESTIONS = [
	"Make it shorter",
	"Add more detail about key points",
	"Change tone to more formal",
	"Generate social media version",
	"Create bullet point summary",
	"Focus more on the technical aspects",
	"Remove the marketing language",
	"What are the key takeaways?",
	"Suggest images for each section",
];

function generateLocalSuggestions(text: string): string[] {
	const suggestions = new Set(BASE_SUGGESTIONS);
	if (text.length > 1500) {
		suggestions.add("Make it shorter");
	}
	if (!/conclusion/i.test(text)) {
		suggestions.add("Add a conclusion with a clear call-to-action");
	}
	if (!/bullet/i.test(text)) {
		suggestions.add("Create bullet point summary");
	}
	return Array.from(suggestions).slice(0, 6);
}

export interface UseSuggestionsOptions {
	content: string;
	serverSuggestions?: string[];
}

export interface UseSuggestionsReturn {
	suggestions: string[];
	quickActions: string[];
}

export function useSuggestions({
	content,
	serverSuggestions,
}: UseSuggestionsOptions): UseSuggestionsReturn {
	const suggestions = useMemo(() => {
		if (serverSuggestions && serverSuggestions.length > 0) {
			return serverSuggestions;
		}
		return generateLocalSuggestions(content);
	}, [content, serverSuggestions]);

	const quickActions = useMemo(() => suggestions.slice(0, 6), [suggestions]);

	return {
		suggestions,
		quickActions,
	};
}

export { generateLocalSuggestions };
