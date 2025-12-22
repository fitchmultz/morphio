"use client";

import type { FC } from "react";

interface SkeletonProps {
	className?: string;
	variant?: "default" | "card" | "text";
}

export const Skeleton: FC<SkeletonProps> = ({
	className = "",
	variant = "default",
}) => {
	const baseClasses = "animate-pulse rounded-lg";
	const variantClasses = {
		default: "bg-gray-200 dark:bg-gray-700/50",
		card: "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700",
		text: "bg-gray-200 dark:bg-gray-700 h-4 w-3/4",
	};

	return (
		<output
			className={`${baseClasses} ${variantClasses[variant]} ${className}`}
			aria-label="Loading..."
			aria-busy="true"
		/>
	);
};
