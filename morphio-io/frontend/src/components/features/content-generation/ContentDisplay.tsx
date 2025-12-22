import dynamic from "next/dynamic";
import type { ComponentPropsWithoutRef } from "react";
import React, { useState } from "react";
import { FaChevronDown, FaCopy, FaDownload } from "react-icons/fa";
import remarkGfm from "remark-gfm";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import logger from "@/lib/logger";
import { notifySuccess, notifyWarning } from "@/lib/toast";
import { exportAsHtml, exportAsMarkdown, exportAsText } from "@/utils/export";

const ReactMarkdown = dynamic(() => import("react-markdown"), { ssr: false });

interface ContentDisplayProps {
	content: string;
	title?: string;
	showCopyButton?: boolean;
	className?: string;
	showAsCard?: boolean;
}

type CodeProps = ComponentPropsWithoutRef<"code"> & {
	inline?: boolean;
};

/**
 * Sanitize URL to prevent XSS attacks via javascript: or data: protocols.
 * Only allows http:, https:, mailto:, and tel: protocols.
 * Decodes URL-encoded characters to prevent bypass attacks (e.g., j%61vascript:).
 */
const sanitizeUrl = (url: string | undefined): string => {
	if (!url) return "#";
	try {
		// Decode the URL to handle encoded characters (e.g., %61 for 'a')
		const decodedUrl = decodeURIComponent(url);
		const trimmed = decodedUrl.trim().toLowerCase();

		// Block dangerous protocols
		if (
			trimmed.startsWith("javascript:") ||
			trimmed.startsWith("data:") ||
			trimmed.startsWith("vbscript:")
		) {
			return "#";
		}
		// Allow safe protocols and relative URLs
		if (
			trimmed.startsWith("http://") ||
			trimmed.startsWith("https://") ||
			trimmed.startsWith("mailto:") ||
			trimmed.startsWith("tel:") ||
			trimmed.startsWith("/") ||
			trimmed.startsWith("#") ||
			trimmed.startsWith(".")
		) {
			return url; // Return original URL to preserve case
		}
		// For other URLs (e.g., relative paths without leading /), allow them
		// but block anything with a scheme (colon before first / or #)
		if (/^[^/#]*:/.test(trimmed)) {
			return "#";
		}
		return url; // Return original URL
	} catch {
		// If decoding fails, it's a malformed URI. Block it for safety.
		return "#";
	}
};

const ContentDisplay: React.FC<ContentDisplayProps> = React.memo(
	({
		content,
		title,
		showCopyButton = true,
		className = "",
		showAsCard = true,
	}) => {
		const [showExportMenu, setShowExportMenu] = useState(false);

		const handleExport = (format: "markdown" | "text" | "html") => {
			const exportTitle = title || "content";
			switch (format) {
				case "markdown":
					exportAsMarkdown(content, exportTitle);
					break;
				case "text":
					exportAsText(content, exportTitle);
					break;
				case "html":
					exportAsHtml(content, exportTitle);
					break;
			}
			setShowExportMenu(false);
			notifySuccess(`Downloaded as ${format.toUpperCase()}`);
		};

		const copyToClipboard = async () => {
			try {
				await navigator.clipboard.writeText(content);
				notifySuccess("Content copied to clipboard!");
			} catch (err) {
				logger.warn("Clipboard copy failed:", { err });
				notifyWarning(
					"Could not copy to clipboard. Try selecting and copying manually.",
				);
			}
		};

		const ContentWrapper = ({ children }: { children: React.ReactNode }) => {
			if (showAsCard) {
				return (
					<section className={`morphio-card ${className}`}>{children}</section>
				);
			}
			return <div className={className}>{children}</div>;
		};

		return (
			<ContentWrapper>
				{(title || showCopyButton) && (
					<div className="px-5 py-4 flex justify-between items-center border-b border-gray-200/50 dark:border-gray-700/50">
						{title && <h2 className="morphio-h2">{title}</h2>}
						{showCopyButton && (
							<div className="flex items-center gap-2">
								<button
									type="button"
									onClick={copyToClipboard}
									className="morphio-icon-button text-green-500 hover:text-green-600 dark:text-green-400 dark:hover:text-green-300 hover:bg-green-50 dark:hover:bg-green-900/30"
									title="Copy content"
									aria-label="Copy content to clipboard"
								>
									<FaCopy className="h-4 w-4" />
								</button>
								<div className="relative">
									<button
										type="button"
										onClick={() => setShowExportMenu(!showExportMenu)}
										className="morphio-icon-button flex items-center gap-1 text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30"
										title="Export content"
										aria-label="Export content"
									>
										<FaDownload className="h-4 w-4" />
										<FaChevronDown className="h-3 w-3" />
									</button>
									{showExportMenu && (
										<div className="absolute right-0 mt-1 w-40 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-10">
											<button
												type="button"
												onClick={() => handleExport("markdown")}
												className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
											>
												Download as Markdown
											</button>
											<button
												type="button"
												onClick={() => handleExport("text")}
												className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
											>
												Download as Text
											</button>
											<button
												type="button"
												onClick={() => handleExport("html")}
												className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
											>
												Download as HTML
											</button>
										</div>
									)}
								</div>
							</div>
						)}
					</div>
				)}
				<div className="p-6">
					<ErrorBoundary
						fallback={
							<div className="p-4 bg-red-50/80 dark:bg-red-900/20 backdrop-blur-sm border border-red-100 dark:border-red-800/50 rounded-xl">
								<p className="morphio-body-sm text-red-600 dark:text-red-400">
									Failed to render content. Please try again or contact support.
								</p>
							</div>
						}
					>
						<div className="prose prose-lg dark:prose-invert max-w-none">
							<ReactMarkdown
								remarkPlugins={[remarkGfm]}
								components={{
									code: ({
										inline,
										className,
										children,
										...props
									}: CodeProps) => {
										const htmlProps =
											props as React.HTMLAttributes<HTMLElement>;
										// eslint-disable-next-line @typescript-eslint/no-unused-vars
										const _match = /language-(\w+)/.exec(className || "");

										if (inline) {
											return (
												<code
													className={`text-pink-500 dark:text-pink-400 bg-gray-100 dark:bg-gray-800/80 px-1.5 py-0.5 rounded font-mono text-sm ${className || ""}`}
													{...htmlProps}
												>
													{children}
												</code>
											);
										}

										return (
											<div className="not-prose my-4">
												<pre className="bg-gray-100 dark:bg-gray-800/80 p-4 rounded-lg overflow-x-auto border border-gray-200/50 dark:border-gray-700/50">
													<code
														className={`text-pink-500 dark:text-pink-400 font-mono text-sm ${className || ""}`}
														{...htmlProps}
													>
														{children}
													</code>
												</pre>
											</div>
										);
									},
									strong: (props) => (
										<strong className="font-semibold morphio-text" {...props} />
									),
									h1: (props) => (
										<h1
											className="morphio-h1 first:mt-0 mt-8 mb-4"
											{...props}
										/>
									),
									h2: (props) => (
										<h2 className="morphio-h2 mt-6 mb-3" {...props} />
									),
									p: (props) => (
										<p
											className="morphio-body my-4 leading-relaxed"
											{...props}
										/>
									),
									ul: (props) => (
										<ul
											className="list-disc pl-6 my-4 space-y-2 morphio-body"
											{...props}
										/>
									),
									ol: (props) => (
										<ol
											className="list-decimal pl-6 my-4 space-y-2 morphio-body"
											{...props}
										/>
									),
									li: (props) => <li className="pl-2" {...props} />,
									a: ({ href, children, ...props }) => (
										<a
											href={sanitizeUrl(href)}
											className="morphio-link"
											target="_blank"
											rel="noopener noreferrer"
											{...props}
										>
											{children}
										</a>
									),
									table: (props) => (
										<table
											className="w-full my-4 border-collapse border border-gray-200 dark:border-gray-700"
											{...props}
										/>
									),
									th: (props) => (
										<th
											className="px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 morphio-body-sm font-semibold"
											{...props}
										/>
									),
									td: (props) => (
										<td
											className="px-4 py-2 border border-gray-200 dark:border-gray-700 morphio-body-sm"
											{...props}
										/>
									),
								}}
							>
								{content}
							</ReactMarkdown>
						</div>
					</ErrorBoundary>
				</div>
			</ContentWrapper>
		);
	},
);

ContentDisplay.displayName = "ContentDisplay";

export default ContentDisplay;
